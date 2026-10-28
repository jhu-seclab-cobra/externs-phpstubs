"""The abstract machine of the handler extraction: it runs the compiled body of a php-src function over abstract
memory and returns every exit (design-extraction-handlers.md)."""

import collections
import heapq

from handler_expr import FORK_CAP, OFFSET_NAMES, Expressions, type_name
from handler_index import NORETURN, STRUCT_TYPE, THROWERS
from handler_memory import ANYV, SIZE, Fn, Ptr, Region, join_states
from handler_values import assume, exclude, literals, resolve
from handler_prims import EXCEPTION, EXCEPTIONS_REGION, Primitives

CALL_DEPTH = 24
VISIT_CAP = 40
CALL_SLICE = 50000
STACK_REPEAT = 2
RETRIES = 8
JOIN_BATCH = 16
JOINED = ("n", "r")


class Exhausted(Exception):
    """The step budget of the running call or request ran out; ``owner`` is the call whose budget it was and
    ``trail`` the definitions running at that moment, outermost first."""

    def __init__(self, owner=None, trail=()):
        super().__init__()
        self.owner, self.trail = owner, trail

    def culprit(self, depth):
        """The definition running at one level below ``depth``: the callee whose subtree used the budget."""
        return self.trail[depth + 1] if len(self.trail) > depth + 1 else None


def join_by_events(states):
    """States that ran the same events and hold the same pending exception become one state whose differing cells
    are alternatives; states with different event histories or exception states stay apart."""
    groups = {}
    for member in states:
        pending = member.read(EXCEPTIONS_REGION, EXCEPTION)
        groups.setdefault((member.events, member.flags, pending), []).append(member)
    return [join_states(group) if len(group) > 1 else group[0] for group in groups.values()]


class Frame:
    """The activation of one function: its source file, its local variables and whether its run saw only code the
    machine could read."""

    def __init__(self, definition, depth):
        self.definition, self.source, self.depth = definition, definition.source, depth
        self.vars, self.arrays, self.complete, self.created = {}, set(), True, []
        self.types = {}

    def bind(self, state, name, value, array=False):
        rid = f"l:{self.depth}:{name}"
        self.vars[name] = rid
        self.created.append(rid)
        (self.arrays.add if array else self.arrays.discard)(name)
        state.put(rid, Region(ANYV, owner=state.token))
        if value is not None:
            state.write(rid, (), value)

    def release(self, state):
        for rid in self.created:
            state.drop(rid)


class Machine(Expressions, Primitives):
    """Run function bodies. ``policy.interpret(definition)`` says which called functions are read; the rest are
    unknown calls."""

    def __init__(self, index, policy):
        self.index, self.policy = index, policy
        self.global_accessors = {"EG": "executor_globals"}
        self.steps, self.limit, self.owner = 0, 0, None
        self.stack, self.running = [], []
        self.marker = None
        self.opaques = []
        self.hopeless = {}
        self.sites = None

    # -- entry ---------------------------------------------------------------------------------------------------
    def call(self, definition, args, state, budget):
        """The (exits, complete) of one top-level call; exits are (value, state) pairs."""
        self.limit, self.owner = self.steps + budget, None
        self.stack = []
        try:
            return self.run(definition, args, state, 0)
        except Exhausted:
            return [], False

    def run(self, definition, args, state, depth):
        code = self.index.code(definition)
        frame = Frame(definition, depth)
        if code.failure:
            if self.policy.opaque(definition, definition.body):
                self.opaques.append((definition, code.failure))
            return [], False
        frame.types.update(definition.param_types)
        for name, value in zip(definition.params, args):
            frame.bind(state, name, value)
        self.stack.append(definition.name)
        self.running.append(definition)
        try:
            exits = self.execute(frame, code, state)
        finally:
            self.stack.pop()
            self.running.pop()
        for _, exit_state in exits:
            frame.release(exit_state)
        return exits, frame.complete

    # -- statements ----------------------------------------------------------------------------------------------
    def execute(self, frame, code, state):
        waiting, pcs, memo, visits, exits = collections.defaultdict(list), [0], {}, collections.Counter(), []
        waiting[0].append(state)

        def push(pc, st):
            """Queue a state at an instruction. States waiting at a join point are joined once they exceed
            ``JOIN_BATCH``, since the join point joins them all when it is reached. A return is a join point: the states
            that return together are joined per event history and pending exception."""
            if pc not in waiting:
                heapq.heappush(pcs, pc)
            queue = waiting[pc]
            queue.append(st)
            if len(queue) > JOIN_BATCH and code.instrs[pc][0] in JOINED:
                waiting[pc] = join_by_events(queue)

        while pcs:
            pc = heapq.heappop(pcs)
            instr = code.instrs[pc]
            batch = waiting.pop(pc)
            for current in join_by_events(batch) if instr[0] in JOINED else batch:
                self.steps += 1
                if self.steps > self.limit:
                    raise Exhausted(self.owner, tuple(self.running))
                if instr[0] == "n":
                    current = self.admit(frame, code, memo, visits, pc, current)
                if current is not None:
                    getattr(self, "i_" + instr[0])(instr, pc, current, frame, push, exits)
        return exits

    @staticmethod
    def admit(frame, code, memo, visits, pc, state):
        """The state to continue from at a join point, or None when the point has seen it. A loop head keeps the
        join of every state that reached it and continues only while the join grows."""
        visits[pc] += 1
        if visits[pc] > VISIT_CAP:
            frame.complete = False
            return None
        if pc not in code.heads:
            key = (pc, state.key())
            seen, memo[key] = key in memo, None
            return None if seen else state
        key = (pc, state.events, state.flags)
        old = memo.get(key)
        merged = state if old is None else join_states([old, state])
        if old is not None and merged.key() == old.key():
            return None
        memo[key] = merged.fork()
        return merged

    def i_n(self, instr, pc, state, frame, push, exits):
        push(pc + 1, state)

    def i_j(self, instr, pc, state, frame, push, exits):
        push(instr[1], state)

    def i_x(self, instr, pc, state, frame, push, exits):
        for joined in join_by_events([s for _, s in self.ev(instr[1], state, frame)]):
            push(pc + 1, joined)

    def i_o(self, instr, pc, state, frame, push, exits):
        if self.policy.opaque(frame.definition, instr[1]):
            self.opaques.append((frame.definition, instr[1]))
            frame.complete = False
        push(pc + 1, state)

    def i_r(self, instr, pc, state, frame, push, exits):
        if instr[1] is None:
            exits.append((ANYV, state))
            return
        exits.extend(self.ev(instr[1], state, frame))

    def i_b(self, instr, pc, state, frame, push, exits):
        for taken, s in self.branch(instr[1], state, frame):
            push(instr[2] if taken else instr[3], s)

    def i_d(self, instr, pc, state, frame, push, exits):
        _, name, pointer, dims, init, words = instr
        frame.bind(state, name, None, array=bool(dims))
        frame.types[name] = type_name(words)
        if init is None:
            push(pc + 1, state)
            return
        layout = self.index.fields if STRUCT_TYPE in words and not pointer else None
        outcomes = self.declared_value(init, layout, state, frame)
        for value, s in outcomes:
            s.write(frame.vars[name], (), value)
        for joined in join_by_events([s for _, s in outcomes]):
            push(pc + 1, joined)

    def declared_value(self, init, layout, state, frame):
        if init[0] == "init":
            return [(self.initializer(init, layout, state, frame), state)]
        return self.ev(init, state, frame)

    def i_g(self, instr, pc, state, frame, push, exits):
        _, group, starts, end, _ = instr
        source = frame.source
        for k, (number, start) in enumerate(starts):
            fork = state.fork()
            fork.tags = fork.tags | frozenset(literals(source.conditions[(group, number)]))
            push(start, fork)
        if group not in source.otherwise:
            push(end, state)

    def i_s(self, instr, pc, state, frame, push, exits):
        _, subject, cases, default, end = instr
        for value, s in self.ev(subject, state, frame):
            for plain, s2 in self.alts(value, s):
                self.dispatch(plain, cases, default if default is not None else end, s2, frame, push)

    def dispatch(self, value, cases, otherwise, state, frame, push):
        """Send a state to the case its value selects; an unknown value forks over every case and the default."""
        seen = []
        for expression, pc in cases:
            constant = resolve(self.ev(expression, state, frame)[0][0], state)
            if not isinstance(constant, int):
                continue
            fork = state.fork()
            if assume(value, constant, fork):
                push(pc, fork)
                if isinstance(resolve(value, fork), int):
                    return
            seen.append(constant)
        if exclude(value, seen, state):
            push(otherwise, state)

    # -- calls ---------------------------------------------------------------------------------------------------
    def e_call(self, node, state, frame):
        callee, argument_nodes = node[1], node[2]
        if callee[0] == "name" and callee[1] in OFFSET_NAMES:
            return [(SIZE, state)]
        if callee[0] == "name" and callee[1] in self.global_accessors:
            return [(self.load(p, s), s) for p, s in self.l_call(node, state, frame)]
        results = []
        for args, s in self.evaluate_arguments(argument_nodes, state, frame):
            results.extend(self.invoke(callee, args, s, frame))
        return results[:FORK_CAP * 4]

    def evaluate_arguments(self, nodes, state, frame):
        outcomes = [([], state)]
        for node in nodes:
            outcomes = [(args + [value], s2) for args, s in outcomes for value, s2 in self.ev(node, s, frame)]
        return outcomes

    def invoke(self, callee, args, state, frame):
        if callee[0] == "name" and callee[1] not in frame.vars:
            return self.call_name(callee[1], args, state, frame)
        out = []
        for target, s in self.ev(callee, state, frame):
            for plain, s2 in self.alts(target, s):
                out.extend(self.call_value(plain, args, s2, frame))
        return out

    def call_value(self, target, args, state, frame):
        if isinstance(target, Fn):
            return self.call_function(target, args, state, frame)
        if isinstance(target, int) and target == 0:
            return []
        return self.unknown_call(args, state)

    def call_function(self, target, args, state, frame):
        if target.source is None:
            return self.call_name(target.name, args, state, frame)
        found = [d for d in self.index.program.functions.get(target.name, ())
                 if not d.is_macro and d.source.relative == target.source]
        return self.interpret(found, target.name, args, state, frame)

    def call_name(self, name, args, state, frame):
        self.note_marker(args, state)
        prim = getattr(self, "p_" + name, None)
        if prim is not None:
            return prim(args, state, frame)
        if THROWERS.fullmatch(name):
            return self.p_throw(args, state, frame)
        if name in NORETURN:
            return []
        return self.interpret(self.index.definitions(name, frame.source), name, args, state, frame)

    def interpret(self, definitions, name, args, state, frame):
        definitions = [d for d in definitions if self.policy.interpret(d)]
        if not definitions or frame.depth >= CALL_DEPTH or self.stack.count(name) >= STACK_REPEAT:
            return self.unknown_call(args, state)
        out = []
        for k, definition in enumerate(definitions[:FORK_CAP]):
            fork = state if k == len(definitions[:FORK_CAP]) - 1 else state.fork()
            out.extend(self.run_callee(definition, args, fork, frame.depth + 1))
        return out

    def run_callee(self, definition, args, state, depth):
        """The exits of a read callee. A callee whose subtree exhausts the step slice of the call is not read again:
        the direct callee that used the slice joins the unread calls and the call runs once more."""
        failed = self.hopeless.setdefault(id(self.policy), set())
        for _ in range(RETRIES):
            if id(definition) in failed:
                break
            outcome = self.attempt(definition, args, state, depth, failed)
            if outcome is not None:
                return outcome
        return self.unknown_call(args, state)

    def attempt(self, definition, args, state, depth, failed):
        """The exits of one run, unknown when it is incomplete, or None when the slice ran out."""
        attempt, saved, start, outer = state.fork(), self.limit, self.steps, self.owner
        token, level = object(), len(self.running)
        if start + CALL_SLICE < saved:
            self.limit, self.owner = start + CALL_SLICE, token
        try:
            exits, complete = self.run(definition, args, attempt, depth)
        except Exhausted as exhausted:
            if exhausted.owner is not token:
                raise
            culprit = exhausted.culprit(level)
            failed.add(id(culprit or definition))
            self.steps = start
            return None
        finally:
            self.limit, self.owner = saved, outer
        return exits if complete else self.unknown_call(args, state)

    def unknown_call(self, args, state):
        """A call whose callee the machine does not read: the result is unknown and a pointer to local or heap
        memory loses its contents."""
        for argument in args:
            if isinstance(argument, Ptr) and argument.rid[0] in "lhoy" and self.policy.unread_writes(argument):
                state.havoc(argument.rid, argument.path)
        return [(ANYV, state)]

    def run_inline(self, block, state, frame):
        """A GNU statement expression: its statements run in the frame, the value is the last expression."""
        code = self.index.inline(block)
        return self.execute(frame, code, state)

    def note_marker(self, args, state):
        if self.marker is not None and any(a == self.marker for a in args):
            state.events = state.events + (("M",),)

