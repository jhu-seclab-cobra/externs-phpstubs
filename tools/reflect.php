<?php
// Write the reflection oracle of the generated set (design-extraction.md, reflect.php).
//
// Prints one tab-separated line per internal function, method, and class-like
// declaration the running PHP build reflects, sorted:
//   function <name> <return> <param>...
//   method <class>::<name> <return> <param>...
//   class <name> <parent or -> <every interface, comma-separated, or ->
// A parameter is "<name> <type> <flags>", the flags drawn from o (optional),
// r (by reference), v (variadic), or "-" for none. Names are folded; an
// omitted type is mixed, PHP's reading of it.

const ABSENT_TYPE = 'mixed';
const NONE = '-';

function declared_type(?ReflectionType $type): string
{
    return $type === null ? ABSENT_TYPE : (string) $type;
}

function parameter(ReflectionParameter $parameter): string
{
    $flags = ($parameter->isOptional() ? 'o' : '') . ($parameter->isPassedByReference() ? 'r' : '')
        . ($parameter->isVariadic() ? 'v' : '');
    return implode(' ', [$parameter->getName(), declared_type($parameter->getType()), $flags === '' ? NONE : $flags]);
}

function callable_line(string $kind, string $subject, ReflectionFunctionAbstract $callable): string
{
    $returned = $callable->getReturnType() ?? $callable->getTentativeReturnType();
    $fields = [$kind, strtolower($subject), declared_type($returned)];
    return implode("\t", array_merge($fields, array_map('parameter', $callable->getParameters())));
}

function class_lines(ReflectionClass $class): array
{
    $interfaces = array_map('strtolower', $class->getInterfaceNames());
    sort($interfaces);
    $parent = $class->getParentClass();
    $lines = [implode("\t", [
        'class',
        strtolower($class->getName()),
        $parent === false ? NONE : strtolower($parent->getName()),
        $interfaces === [] ? NONE : implode(',', $interfaces),
    ])];
    foreach ($class->getMethods() as $method) {
        if ($method->getDeclaringClass()->getName() === $class->getName()) {
            $lines[] = callable_line('method', $class->getName() . '::' . $method->getName(), $method);
        }
    }
    return $lines;
}

$lines = array_map(
    fn (string $name) => callable_line('function', $name, new ReflectionFunction($name)),
    get_defined_functions()['internal'],
);
foreach (array_merge(get_declared_classes(), get_declared_interfaces(), get_declared_traits()) as $name) {
    $class = new ReflectionClass($name);
    if ($class->isInternal()) {
        $lines = array_merge($lines, class_lines($class));
    }
}
sort($lines);
echo implode("\n", $lines), "\n";
