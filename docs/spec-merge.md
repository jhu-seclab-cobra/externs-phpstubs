# PHP Stubs — Merge Algorithm

Folding the bundled sets, and any consumer sets, into the Merge the
`BuiltinLookup` reads. Entity vocabulary: [model-lookup.md](model-lookup.md);
format entities: commons-phpmodels `docs/model.md`, `model-conditions.md`,
`model-sets.md`.

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
    return read_only(vocab, matrix(rows), inForce)

fold(mounted):
    inForce = {}                                       # subject → condition → unit → (e, rank, position)
    for (position, rank, e) in mounted, in order:      # slots in mount order of the first entry
        require e.condition = none or e.signature = none   # conditional signature → failure
        add slot inForce[e.subject][e.condition] if absent
    for (position, rank, e) in mounted
            sorted by rank ascending, then position ascending, stable:
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
```

`accumulate` and the verification of every reference against the
vocabulary accumulated so far are the set loader's ([model-sets.md] of
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

### Invariants

- After the sort, entries are written in non-decreasing (rank, position)
  order, so the last write per key is the one the correctness condition
  names.
- The first pass fixes the order of subjects and conditions; the second
  pass never adds a slot, so the entry in force never moves a record.
- Writing one key leaves every other key untouched; a subject's other
  units and other conditions are never read during a write.
- Subjects are compared by the format's identity (folded per kind), the
  same identity a lookup key carries.
- The same sets in the same order under the same precedence merge into
  equal entries in force.

### Termination

- Finitely many sets, each with finitely many entries. One linear pass,
  one sort and one more linear pass, no fixpoint.

### Complexity

- O(E log E) time over entries E for the stable sort, O(E) writes; O(K)
  space over distinct keys K ≤ 6E.
