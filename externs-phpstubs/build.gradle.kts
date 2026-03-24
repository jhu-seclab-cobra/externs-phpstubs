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
    testImplementation("org.junit.jupiter:junit-jupiter-api:5.10.2")
}

kotlin {
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

java {
    withSourcesJar()
    withJavadocJar()
}

publishing {
    publications { create<MavenPublication>("maven") { from(components["java"]) } }
}
