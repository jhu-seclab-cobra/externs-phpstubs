# PHP Stubs — Merge Algorithm

Folding the bundled sets, and any extension sets, into the Merge the
Built-in Lookup reads. Entity vocabulary: [model-lookup.md](model-lookup.md);
format entities: commons-phpmodels `docs/model.md`, `model-conditions.md`,
`model-sets.md`.

## Algorithm: Merge Sets

### Problem

Input: an ordered list of document sets, each already decoded and verified
by the format library's set loader (entries, accumulated vocabulary,
policy, set provenance; a mapped set arrives translated into the Canonical
Vocabulary), and the default Precedence over verification kinds. Output:
the accumulated vocabulary, the policy matrix, and one Statement per
(subject, condition, unit) key stated by any set — five units: signature,
value (returns with propagation), sources, sinks, sanitizers — each
Statement remembering the set that stated it. Correctness: per key the
highest-ranked set's Statement is in force and, among equal ranks, the
later mounted; a Statement never replaces one with a different key; the
result is immutable and equal for equal inputs.

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
    statements = fold(mounted)
    return frozen(vocab, matrix(rows), statements)

fold(mounted):
    statements = {}                                    # (subject, condition, unit) → Statement
    for (position, rank, e) in mounted
            sorted by rank ascending, then position ascending, stable:
        require e.condition = none or e.signature = none   # conditional signature → failure
        for unit in declaredUnits(e):
            statements[(e.subject, e.condition, unit)] = Statement(e[unit], rank, position)
    return statements                                  # the last write per key is in force

declaredUnits(e):
    { signature  if e.signature declared
      value      if e.body.returns declared            # returns + propagation
      sources    if e.body.sources declared
      sinks      if e.body.sinks declared
      sanitizers if e.body.sanitizers declared }
```

`accumulate` and the verification of every reference against the
vocabulary accumulated so far are the set loader's ([model-sets.md] of
the format library): the loader is invoked once per set with the
vocabulary the previous sets produced, so an undeclared name fails at that
set's load. Every format rule — subject spellings, ports, sections,
conditions, signatures, arity, mapping translation and the dropping of
elements left without a name — is applied there and not restated here.

Reading a record from `statements` is a key scan: the record of subject
`s` exists when any key starts with `s`; its signature is the
`(s, none, signature)` Statement or none; its Facts are the
elements of every Statement whose key starts with `s`, each carrying that
key's condition.

### Edge Cases

- A set declaring one unit for a subject another set declared a different
  unit for replaces only its own unit.
- Two entries for one subject with equal conditions (or both
  unconditional) replace per unit by rank, then by mount order; a
  different condition is a different key and coexists.
- A set without a provenance document mounts at the precedence's default
  rank, manual under the default precedence.
- The generated set and a manual set stating the same key: the manual
  Statement is in force whatever the mount order.
- Two manual sets stating the same key: the later mounted is in force.
  Among the bundled sets this makes taint rules override taint, and among
  extension sets the later supplied override the earlier.
- An empty list of sets merges into an empty result; every lookup answers
  no record.

### Invariants

- After the sort, Statements are written in non-decreasing (rank, position)
  order, so the last write per key is the one the correctness condition
  names.
- Writing one key leaves every other key untouched; a subject's other
  units and other conditions are never read during a write.
- Subjects are compared by the format's identity (folded per kind), the
  same identity a lookup key carries.
- The same sets in the same order under the same precedence merge into
  equal Statements.

### Termination

- Finitely many sets, each with finitely many entries. One sort and one
  linear pass, no fixpoint.

### Complexity

- O(E log E) time over entries E for the stable sort, O(E) writes; O(K)
  space over distinct keys K ≤ 5E.
