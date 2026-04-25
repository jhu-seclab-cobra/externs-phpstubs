plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "0.9.0"
}

rootProject.name = "externs-phpstubs"

include("jhu-seclab-cobra-externs-phpstubs")
project(":jhu-seclab-cobra-externs-phpstubs").projectDir = file("externs-phpstubs")
