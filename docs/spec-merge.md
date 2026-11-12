# PHP Stubs — Merge Algorithm

Folding the bundled sets, and any consumer sets, into the Set Merge
the `BuiltinLookup` reads. Entity vocabulary: [model-lookup.md](model-lookup.md);
format entities: [commons-phpmodels model.md](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/model.md), [model-conditions.md](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/model-conditions.md),
[model-sets.md](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/model-sets.md).

## Algorithm: Merge Sets

### Problem

Input: an ordered list of document sets, each already decoded and verified
by the format library's set loader (entries, accumulated vocabulary,
policy, set provenance; a mapped set arrives translated into the Canonical
Vocabulary), and the default Precedence over verification kinds. Output:
the accumulated vocabulary, the policy matrix, and the entry in force for
each (subject, condition, unit) key stated by any set — six units:
signature, value (returns with propagation and characters), sources,
sinks, sanitizers, throws — each with the rank and position of the set
that stated it, keys ordered by the mount order of their subject's and
condition's first entry. Correctness: per key the highest-ranked set's
entry is in force and, among equal ranks, the later mounted; an entry is
in force only for the keys it states; the result is immutable and equal
for equal inputs.

### Steps

```
merge(sets, precedence):
    vocab = ∅ ; rows = [] ; mounted = []
    for (position, set) in sets, in order:
        vocab = accumulate(vocab, set.vocabulary)      # loader: redeclaration must be identical
        rows += set.policy
        rank = rank(precedence, set.provenance.verification or precedence.default)
        for entry in set.entries:
            mounted.append((position, rank, entry))
    inForce = fold(mounted)
    return read_only(vocab, matrix(rows), inForce, keyClassAliases(inForce))

fold(mounted):
    inForce = {}                                       # subject → condition → unit → (e, rank, position)
    for (position, rank, e) in mounted, in order:      # slots in mount order of the first entry
        require e.condition = none or e.signature = none   # conditional signature → failure
        add slot inForce[e.subject][e.condition] if absent
    for (position, rank, e) in mounted
            sorted by numeric rank descending, then position ascending, stable:
        for unit in declaredUnits(e):
            inForce[e.subject][e.condition][unit] = (e, rank, position)
    return inForce                                     # the last write per key is in force

declaredUnits(e):
    { signature  if e.signature declared
      value      if e.body.returns declared            # returns + propagation + characters
      sources    if e.body.sources declared
      sinks      if e.body.sinks declared
      sanitizers if e.body.sanitizers declared
      throws     if e.body.throws declared }       # the empty set is declared

keyClassAliases(inForce):                              # after every declaration subject is keyed
    classes = { key(r.subject) → r  for each class record r, in key order }
    for r in the class records, in key order:
        for a in r.signature.aliases:                  # the signature in force
            require key(a) not in classes              # a declaration subject or an earlier alias → failure
            classes[key(a)] = r
    return classes
```

The alias-key step inserts keys into the existing class map and adds no
record: a record keeps its declaration subject and its position. Its
aliases are those of the signature in force, so a replacing signature that
omits them removes their keys (a replacing signature replaces the whole
signature: [commons-phpmodels model-declarations.md](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/model-declarations.md), Invariants). `key(a)` is the class subject the alias
spelling parses to.

`accumulate` and the verification of every reference against the
vocabulary accumulated so far are the set loader's ([model-sets.md](https://github.com/jhu-seclab-cobra/commons-phpmodels/blob/56feb9d33a3cf8445eb74f01eb22279ed71f5674/docs/model-sets.md) of
the format library): the loader is invoked once per set with the
vocabulary the previous sets produced, so an undeclared name fails at that
set's load. Every format rule — subject spellings, ports, sections,
conditions, signatures, arity, mapping translation and the dropping of
elements left without a name — is applied there and not restated here.

Reading a record from `inForce` is a key scan: the record of subject `s`
exists when any key starts with `s`; its signature is that of the entry in
force for `(s, none, signature)`, or none; its Facts are the elements of
every entry in force for a key that starts with `s`, each carrying that
key's condition, in condition order, then unit order (signature, value,
sources, sinks, sanitizers, throws), then document order.

### Edge Cases

- A set declaring one unit for a subject another set declared a different
  unit for replaces only its own unit.
- Two entries for one subject with equal conditions (or both
  unconditional) replace per unit by rank, then by mount order; a
  different condition is a different key and coexists.
- A set without a provenance document mounts at the precedence's default
  rank, manual under the default precedence.
- The generated set and a manual set stating the same key: the manual
  entry is in force whatever the mount order.
- Two manual sets stating the same key: the later mounted is in force.
  Among the bundled sets this makes taint rules override taint, and among
  consumer sets the later supplied override the earlier.
- An empty list of sets merges into an empty result; every lookup answers
  no record.
- A class record whose signature states the alias `dom\domexception` is
  keyed under `domexception` and `dom\domexception`; both keys read the same
  record.
- Class `a` states the alias `b` while class `b` is declared, or classes
  `a` and `b` both state the alias `x\c`: the alias-key step fails with
  `StubIndexInvalidException`.

### Invariants

- Numeric rank 0 is strongest; sorting by decreasing numeric rank and increasing mount position makes the last write per key the highest-precedence, latest-mounted entry.
- The first pass fixes the order of subjects and conditions; the second
  pass never adds a slot, so the entry in force never moves a record.
- Writing one key leaves every other key untouched; a subject's other
  units and other conditions are never read during a write.
- Subjects are compared by the format's identity (folded per kind), the
  same identity a lookup key carries.
- The same sets in the same order under the same precedence merge into
  equal entries in force.
- The alias-key step preserves the lookup relations and enumeration
  invariants of [model-lookup.md](model-lookup.md).

### Termination

- Finitely many sets, each with finitely many entries. One linear pass,
  one sort, one more linear pass and one finite pass over the alias keys,
  no fixpoint.

### Complexity

- O(E log E + A) time over entries E for the stable sort, O(E) writes and
  O(A) alias insertions; O(E + K + A) additional space over distinct keys K ≤ 6E before the
  alias step, with A the aliases in the class signatures in force; mounted-entry materialization and sorting retain O(E) entries. Vocabulary and policy storage add their retained sizes V and P. Canonical-name
  construction adds the cost below.

### Example

```php
<?php
var_dump(strlen('abc'));
```

For this call, suppose a generated Model and a manual Model both state an unconditional Value unit for `strlen`. The manual unit is in force regardless of mount position. The numeric rank from the dependency is zero for manual and one for generated, so the fold writes generated first and manual last. The PHP result remains `int(3)`; the lookup supplies assertions, not concrete evaluation.

## Canonical Name Query

### Problem

Input: canonical function/class records whose effective Signature is present, and a pattern of literal text and independent string gaps. Output: every canonical record accepted by the complete pattern, once; class-alias keys contribute no additional declarations. The [lookup model](model-lookup.md) owns record eligibility and exact-lookup semantics.

### Steps

1. During final record construction, insert each eligible canonical name into its kind’s trie and attach the existing record to its terminal, before alias expansion.
2. Compile the pattern into positions: a literal consumes its character and advances; a gap consumes a character without advancing or advances without consuming.
3. Start at position zero, close empty gap transitions, and combine that state with the state after one leading root separator.
4. Walk the trie depth first. Advance pattern states for each child character and prune a child when no state remains.
5. At an accepting terminal emit the canonical record once. Keep DFS frames for child position and active pattern positions; discard a frame after its children end.
6. Existence consumes the first result; full lookup consumes every result. Single-name matching applies the same transitions to that name.

### Invariants

- Each reached trie prefix carries exactly the pattern positions accepting that prefix.
- Only complete-pattern acceptance emits a terminal; a prefix match does not.
- No class-alias key is inserted into the query trie.
- Each emitted terminal has an effective Signature and is emitted once.

### Termination

A trie has finitely many nodes and each DFS frame visits each child once. Pattern closure advances only through finitely many positions. Existence may stop earlier.

### Complexity

Construction takes O(S) time and O(S + N) storage per effective merge. Query setup takes O(p); traversal takes O(pQ + Z) worst-case time and O(pL) live DFS state. S is eligible name text, N terminal identities, Q visited trie nodes, L maximum name length, p pattern size and Z outputs. Single-name matching takes O(pT) time and O(p) live state for name length T. Include summed trie storage across live merges.

### Edge Cases

- A broad pattern with no result may visit the entire trie.
- A gap accepts an empty string and each occurrence is independent.
- A pattern may include one leading root separator without duplicating canonical outputs.

### Example

```php
<?php
function dispatch(string $suffix): void {
    $name = 'str' . $suffix;
    $name('example');
}
```

A caller representing this name as literal `str` followed by a gap receives canonical function records with an effective Signature and matching names, such as `strlen`; the lookup does not evaluate the PHP call or choose a suffix value.
