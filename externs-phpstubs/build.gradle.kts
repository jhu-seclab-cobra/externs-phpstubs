plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlinx.kover)
    alias(libs.plugins.ktlint)
    alias(libs.plugins.detekt)
    `java-library`
    `maven-publish`
}

group = "edu.jhu.cobra"
version = "0.1.0"

val jvmVersion =
    libs.versions.javaTarget
        .get()
        .toInt()

repositories {
    mavenCentral()
}

dependencies {
    implementation(libs.snakeyaml)
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

tasks.processResources {
    doLast {
        val stubsDir = destinationDir.resolve("stubs")
        if (stubsDir.isDirectory) {
            val yamlFiles =
                stubsDir
                    .walkTopDown()
                    .filter { it.extension == "yaml" }
                    .map { it.relativeTo(stubsDir).path }
                    .sorted()
                    .toList()
            stubsDir.resolve("index.txt").writeText(yamlFiles.joinToString("\n") + "\n")
        }
    }
}

tasks.processTestResources {
    doLast {
        val stubsDir = destinationDir.resolve("stubs-test")
        if (stubsDir.isDirectory) {
            val yamlFiles =
                stubsDir
                    .walkTopDown()
                    .filter { it.extension == "yaml" }
                    .map { it.relativeTo(stubsDir).path }
                    .sorted()
                    .toList()
            stubsDir.resolve("index.txt").writeText(yamlFiles.joinToString("\n") + "\n")
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
