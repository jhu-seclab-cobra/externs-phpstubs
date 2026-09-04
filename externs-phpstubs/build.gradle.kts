plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlinx.kover)
    alias(libs.plugins.ktlint)
    alias(libs.plugins.detekt)
    `java-library`
    `maven-publish`
}

group = "edu.jhu.cobra"
version = "0.2.0"

val jvmVersion =
    libs.versions.javaTarget
        .get()
        .toInt()

repositories {
    mavenCentral()
    maven { url = uri("https://jitpack.io") }
}

dependencies {
    api(libs.cobra.commons.phpmodels)
    testImplementation(kotlin("test"))
    testImplementation(libs.junit.jupiter.api)
}

kotlin {
    explicitApi()
    jvmToolchain {
        languageVersion.set(JavaLanguageVersion.of(jvmVersion))
    }
}

tasks.test {
    useJUnitPlatform {
        if (!project.hasProperty("performance")) {
            excludeTags("performance")
        }
    }
    if (project.hasProperty("performance")) {
        jvmArgs("-Xmx2g", "-Xms1g")
        testLogging {
            showStandardStreams = true
        }
    }
}

// One index-generation action for both resource tasks; the map names each task's models directory.
// Inline lambda (not a script function) keeps the action configuration-cache serializable.
val modelIndexDirNames = mapOf("processResources" to "models", "processTestResources" to "models-test")

tasks.withType<ProcessResources>().configureEach {
    val modelsDirName = modelIndexDirNames[name] ?: return@configureEach
    doLast {
        val modelsDir = destinationDir.resolve(modelsDirName)
        if (modelsDir.isDirectory) {
            val yamlFiles =
                modelsDir
                    .walkTopDown()
                    .filter { it.extension == "yaml" }
                    .map { it.relativeTo(modelsDir).path }
                    .sorted()
                    .toList()
            modelsDir.resolve("index.txt").writeText(yamlFiles.joinToString("\n") + "\n")
        }
    }
}

java {
    withSourcesJar()
    withJavadocJar()
}

publishing {
    publications { create<MavenPublication>("maven") { from(components["java"]) } }
}

ktlint {
    version.set("1.5.0")
    verbose.set(true)
    android.set(false)
    outputToConsole.set(true)
    filter {
        exclude("**/generated/**")
        exclude("**/build/**")
    }
}

detekt {
    // Resolve the repository's own config even when this module is embedded
    // as a subproject of an enclosing build.
    config.setFrom(files("${projectDir.parentFile}/config/detekt/detekt.yml"))
    buildUponDefaultConfig = true
    parallel = true
}
