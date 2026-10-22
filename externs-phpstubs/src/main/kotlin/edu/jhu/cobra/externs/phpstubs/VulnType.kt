package edu.jhu.cobra.externs.phpstubs

import edu.jhu.cobra.commons.phpmodels.VulnTypeId

/**
 * The vulnerability types of the canonical vocabulary, one constant per name `vocabulary/vocabulary.yaml`
 * declares, so a consumer filters facts without spelling a string. A vulnerability type a consumer set adds has
 * no constant and is compared by its [VulnTypeId].
 *
 * @property id The interned identifier the vocabulary document declares.
 */
public enum class VulnType(
    public val id: VulnTypeId,
) {
    SQLI(VulnTypeId("sqli")),
    CMDI(VulnTypeId("cmdi")),
    CODEI(VulnTypeId("codei")),
    XSS(VulnTypeId("xss")),
    HEADERI(VulnTypeId("headeri")),
    SSRF(VulnTypeId("ssrf")),
    PATHTRAV(VulnTypeId("pathtrav")),
    FILEINC(VulnTypeId("fileinc")),
    DESER(VulnTypeId("deser")),
    CALLABLEI(VulnTypeId("callablei")),
    LDAPI(VulnTypeId("ldapi")),
    XPATHI(VulnTypeId("xpathi")),
    SCHEMEI(VulnTypeId("schemei")),
}
