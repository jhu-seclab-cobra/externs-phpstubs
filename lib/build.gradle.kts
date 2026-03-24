plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlinx.kover)
    `java-library`
    `maven-publish`
}

group = "edu.jhu.cobra"
version = "0.1.0"

val jvmVersion = libs.versions.javaTarget.get().toInt()

repositories {
    mavenCentral()
}

dependencies {
    api(libs.cobra.commons.value)
    testImplementation(kotlin("test"))
}

kotlin {
    jvmToolchain {
        languageVersion.set(JavaLanguageVersion.of(jvmVersion))
    }
}

java {
    withSourcesJar()
    withJavadocJar()
}

publishing {
    publications { create<MavenPublication>("maven") { from(components["java"]) } }
}
