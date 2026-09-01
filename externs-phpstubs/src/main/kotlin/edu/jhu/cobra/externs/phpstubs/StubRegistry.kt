package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.ClassConstantSubject
import edu.jhu.cobra.commons.phpmodels.ClassSubject
import edu.jhu.cobra.commons.phpmodels.ConstantSubject
import edu.jhu.cobra.commons.phpmodels.FunctionSubject
import edu.jhu.cobra.commons.phpmodels.MethodSubject
import edu.jhu.cobra.commons.phpmodels.PropertySubject

/** Immutable registry of loaded stub entries, one map per subject kind, keyed by subject. */
public data class StubRegistry(
    val functions: Map<FunctionSubject, StubEntry<FunctionSubject>>,
    val classes: Map<ClassSubject, StubEntry<ClassSubject>>,
    val methods: Map<MethodSubject, StubEntry<MethodSubject>>,
    val constants: Map<ConstantSubject, StubEntry<ConstantSubject>>,
    val classConstants: Map<ClassConstantSubject, StubEntry<ClassConstantSubject>>,
    val properties: Map<PropertySubject, StubEntry<PropertySubject>>,
)
