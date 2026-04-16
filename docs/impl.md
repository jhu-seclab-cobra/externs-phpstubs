# PHP Stubs Implementation Notes

## Libraries

- `commons-value` — IR value types (`IValue`, `ListVal`, `StrVal`, `MapVal`). Exposed as `api` dependency. Consumer uses `DftByteArraySerializerImpl` to deserialize raw bytes from `getFuncRawData()`/`getClassRawData()`/etc.

## APIs

- **[DftByteArraySerializerImpl]** `DftByteArraySerializerImpl().deserialize(bytes)` — reconstruct `IValue` from raw stub bytes. Consumer-side only; library does not call this.
- **[DataInputStream]** `DataInputStream(bufferedStream).readInt()` / `.readByte()` / `.readUTF()` — binary index parsing. Big-endian, Java-standard `Modified UTF-8`.

## Developer Instructions

- Binary index: `builtin.bin` at classpath `/stubs/builtin.bin`. Format: 5-byte header (magic `0x43534253` + version `1`), four sections (functions, classes, methods, constants). Each section: entry count (int), then `[UTF key][int value-length][bytes]` per entry.
- Raw value bytes are `DftByteArraySerializerImpl` output from `commons-value`. Type tags: `0x0C` = `ListVal`, `0x01` = `StrVal`.
- `StubSection.extractExtension` parses only the first element of a `ListVal` to extract extension name — avoids full deserialization.
- Performance tests excluded by default. Run with `./gradlew test -Pperformance`. JVM flags `-Xmx2g -Xms1g` applied in performance mode only.
