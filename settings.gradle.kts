plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "0.9.0"
}

rootProject.name = "externs-phpstubs"

// Only include commons-value when building standalone (not as a composite build).
// When included by a parent project, the parent is responsible for providing commons-value.
if (gradle.parent == null) {
    includeBuild("extern/commons-value") {
        name = "commons-value"
        dependencySubstitution {
            substitute(module("com.github.jhu-seclab-cobra:commons-value")).using(project(":jhu-seclab-cobra-commons-value"))
        }
    }
}

// Unique module identifier to avoid composite build name collisions (gradle/gradle#847)
include("jhu-seclab-cobra-externs-phpstubs")
project(":jhu-seclab-cobra-externs-phpstubs").projectDir = file("lib")
