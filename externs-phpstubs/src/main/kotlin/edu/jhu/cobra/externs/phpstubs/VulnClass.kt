package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.VulnClassId

/**
 * The danger categories of the canonical vocabulary, one constant per name `vocabulary/vocabulary.yaml`
 * declares, so a consumer filters facts without spelling a string. A category an extension set adds has
 * no constant and is compared by its [VulnClassId].
 *
 * @property id The interned identifier the vocabulary document declares.
 */
public enum class VulnClass(
    public val id: VulnClassId,
) {
    SQLI(VulnClassId("sqli")),
    CMDI(VulnClassId("cmdi")),
    CODEI(VulnClassId("codei")),
    XSS(VulnClassId("xss")),
    HEADERI(VulnClassId("headeri")),
    SSRF(VulnClassId("ssrf")),
    PATHTRAV(VulnClassId("pathtrav")),
    FILEINC(VulnClassId("fileinc")),
    DESER(VulnClassId("deser")),
    CALLABLEI(VulnClassId("callablei")),
    LDAPI(VulnClassId("ldapi")),
    XPATHI(VulnClassId("xpathi")),
}
