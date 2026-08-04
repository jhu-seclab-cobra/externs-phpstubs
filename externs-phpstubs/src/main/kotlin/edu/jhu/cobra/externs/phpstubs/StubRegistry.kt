package edu.jhu.cobra.externs.phpstubs

/** Immutable registry of parsed PHP stub records. All maps keyed by normalized name. */
public data class StubRegistry(
    val functions: Map<String, StubRecord.Function>,
    val classes: Map<String, StubRecord.PhpClass>,
    val methods: Map<String, StubRecord.Method>,
    val constants: Map<String, StubRecord.Constant>,
    val classConstants: Map<String, StubRecord.ClassConstant>,
    val properties: Map<String, StubRecord.Property>,
)
