"""Starter catalog of study posts.

LinkedIn addresses are references. Article choices fill the form with a
public Microsoft Learn page. Reading goals fill the goal sentence only.
"""

from dataclasses import dataclass

OWN_LINK = "Paste my own link"
NO_READING_GOAL = "No reading goal"
READING_GOAL_CAPTION = (
    "This is a study goal. Paste a public page or the lesson words before you press Study this page."
)

_IAM = "IAM"
_SECURITY = "IAM Security"
_TENANT = "Microsoft 365 Tenant"
_M365 = "Microsoft 365"
_PRIVILEGED = "Privileged access"
_GUESTS = "Apps and guests"
_DEVICES = "Devices"
_DATA = "Data protection"


@dataclass(frozen=True)
class SampleLink:
    """One catalog post."""

    group: str
    title: str
    posted_on: str
    linkedin_url: str
    role: str
    learn_url: str
    goal: str


def _article(
    group: str,
    title: str,
    posted_on: str,
    linkedin_url: str,
    learn_url: str,
    goal: str,
) -> SampleLink:
    return SampleLink(group, title, posted_on, linkedin_url, "article", learn_url, goal)


def _goal(group: str, title: str, posted_on: str, linkedin_url: str) -> SampleLink:
    return SampleLink(group, title, posted_on, linkedin_url, "goal", "", title)


SAMPLE_LINKS: tuple[SampleLink, ...] = (
    _article(
        _IAM,
        "Microsoft Entra ID / Azure AD in IAM",
        "9/28/2026",
        "https://www.linkedin.com/posts/microsoftentraid-azuread-iam-share-7508754234138505217-CDhV",
        "https://learn.microsoft.com/en-us/entra/fundamentals/whatis",
        "Explain what Microsoft Entra ID does.",
    ),
    _article(
        _IAM,
        "Active Directory and Windows Server in IAM",
        "9/28/2026",
        "https://www.linkedin.com/posts/activedirectory-windowsserver-iam-share-7510208637324300288-j8fA",
        "https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/active-directory-domain-services-overview",
        "Explain what Active Directory Domain Services does.",
    ),
    _article(
        _IAM,
        "Active Directory / Windows Server for system administration",
        "9/30/2026",
        "https://www.linkedin.com/posts/mdhossain-cloud_activedirectory-windowsserver-systemadministration-share-7510272566440386560-zlkA",
        "https://learn.microsoft.com/en-us/windows-server/administration/server-manager/server-manager",
        "Describe how Server Manager is used to administer Windows Server.",
    ),
    _article(
        _IAM,
        "On-Premises Active Directory vs. Microsoft Entra ID",
        "10/10/2026",
        "https://www.linkedin.com/posts/arun-jayachandran-739942183_microsoftentraid-activedirectory-identityandaccessmanagement-share-7514395344093265920-U4UC/",
        "https://learn.microsoft.com/en-us/entra/fundamentals/compare",
        "Compare on-premises Active Directory with Microsoft Entra ID.",
    ),
    _article(
        _IAM,
        "Creating an Active Directory user is only the beginning",
        "10/11/2026",
        "https://www.linkedin.com/posts/jamshed-ghafoor_itsupport-activedirectory-windowsserver-share-7493113779488968706-e7kd/",
        "https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage-user-accounts-in-windows-server",
        "Describe how to create and manage an Active Directory user.",
    ),
    _article(
        _IAM,
        "Active Directory / Windows Server / IT infrastructure",
        "10/15/2026",
        "https://www.linkedin.com/posts/i-am-manish-sharma_activedirectory-windowsserver-itinfrastructure-share-7515818106947153920-tiEM/",
        "https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/forest-design-models",
        "Explain how an Active Directory forest is designed.",
    ),
    _article(
        _IAM,
        "RBAC Implementation: Managing Access vs Creating Roles",
        "10/22/2026",
        "https://www.linkedin.com/posts/sujit-acharya-354123209_iam-rbac-identitygovernance-share-7517985564491468800-TZsc/",
        "https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/concept-understand-roles",
        "Explain how Microsoft Entra roles control access.",
    ),
    _article(
        _IAM,
        "Active Directory Authentication in Windows Server Explained",
        "10/23/2026",
        "https://www.linkedin.com/posts/activedirectory-windowsserver-systemadministrator-share-7517902999487365120-aaCM/",
        "https://learn.microsoft.com/en-us/windows-server/security/windows-authentication/windows-authentication-overview",
        "Explain how Windows authentication works.",
    ),
    _article(
        _IAM,
        "Active Directory vs. Microsoft Entra ID: Key Differences",
        "10/24/2026",
        "https://www.linkedin.com/posts/mohan-chimakurthy_activedirectory-microsoftentraid-azuread-share-7517888814812516352-obr_/",
        "https://learn.microsoft.com/en-us/entra/fundamentals/compare",
        "Compare on-premises Active Directory with Microsoft Entra ID.",
    ),
    _article(
        _SECURITY,
        "Microsoft Entra ID MFA (IAM)",
        "9/28/2026",
        "https://www.linkedin.com/posts/microsoftentraid-mfa-iam-share-7508391742270951426-5NO_",
        "https://learn.microsoft.com/en-us/entra/identity/authentication/concept-mfa-howitworks",
        "Explain how Microsoft Entra multifactor authentication works.",
    ),
    _article(
        _SECURITY,
        "Conditional Access: what if knowing the identity is not enough?",
        "10/1/2026",
        "https://www.linkedin.com/posts/khushaboo-joshi-62830915b_microsoftentraid-conditionalaccess-iam-share-7510075981337042945-gF3H",
        "https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview",
        "Explain what Conditional Access checks before it allows a sign-in.",
    ),
    _article(
        _SECURITY,
        "Zero Trust, cybersecurity and identity security",
        "10/20/2026",
        "https://www.linkedin.com/posts/zerotrust-cybersecurity-identitysecurity-share-7517395787677540352-a9Ai/",
        "https://learn.microsoft.com/en-us/security/zero-trust/deploy/identity",
        "Explain the identity part of Zero Trust.",
    ),
    _article(
        _SECURITY,
        "Authentication Methods in Microsoft Entra ID",
        "10/21/2026",
        "https://www.linkedin.com/posts/khushaboo-joshi-62830915b_iam-microsoftentraid-authentication-share-7518166079614078976-A_4k/",
        "https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-methods",
        "Explain the authentication methods in Microsoft Entra ID.",
    ),
    _article(
        _SECURITY,
        "Microsoft Entra Connect Sync: important change by April 7, 2027",
        "10/24/2026",
        "https://www.linkedin.com/posts/bassel-jammal-158333110_microsoft365-microsoftentra-azure-share-7519307109122064386-c6Oq/",
        "https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/harden-update-ad-fs-pingfederate",
        "Explain the Entra Connect Sync upgrade required by April 7, 2027.",
    ),
    _article(
        _TENANT,
        "Microsoft 365 Admin Routine: Security, Productivity and Compliance",
        "9/23/2026",
        "https://www.linkedin.com/posts/ihsan04042000_microsoft365-microsoft365admin-itsupport-share-7507404154244526080-KopB",
        "https://learn.microsoft.com/en-us/microsoft-365/admin/admin-overview/admin-center-overview",
        "Explain what the Microsoft 365 admin center is for.",
    ),
    _article(
        _TENANT,
        "Microsoft Purview, Information Protection Architecture",
        "9/24/2026",
        "https://www.linkedin.com/posts/rajeevyadavofficial_microsoftpurview-informationprotection-datasecurity-share-7508714626797228033-nbuF",
        "https://learn.microsoft.com/en-us/purview/information-protection",
        "Explain what Microsoft Purview Information Protection does.",
    ),
    _article(
        _TENANT,
        "Microsoft 365 Tenant Architecture",
        "9/26/2026",
        "https://www.linkedin.com/posts/ihsan04042000_microsoft365-microsoftentraid-intune-share-7508847146809516032-f_7_",
        "https://learn.microsoft.com/en-us/microsoft-365/solutions/tenant-management-tenants",
        "Explain what a Microsoft 365 tenant is.",
    ),
    _article(
        _TENANT,
        "How to Sync / Migrate Active Directory Objects to Microsoft Entra ID",
        "10/20/2026",
        "https://www.linkedin.com/posts/mangeshghate_microsoftentraid-activedirectory-microsoft365-share-7517444793283776512--GtS/",
        "https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-sync-whatis",
        "Explain how Entra Connect Sync moves Active Directory objects to Microsoft Entra ID.",
    ),
    _article(
        _TENANT,
        "Microsoft 365 Employee Offboarding: do more than delete the user",
        "10/20/2026",
        "https://www.linkedin.com/posts/elvis-odihiri-244a103a4_microsoft365-microsoftentra-azuread-share-7514682382038499328-ot-Z/",
        "https://learn.microsoft.com/en-us/microsoft-365/admin/add-users/remove-former-employee",
        "Explain the steps for removing a former employee from Microsoft 365.",
    ),
    _article(
        _TENANT,
        "Microsoft 365, Intune, Defender Integration for IT Management",
        "10/21/2026",
        "https://www.linkedin.com/posts/prasuna-chandaa_microsoft365-microsoftintune-microsoftdefender-share-7516342645040824320-pt4f/",
        "https://learn.microsoft.com/en-us/intune/device-security/microsoft-defender/configure-integration",
        "Explain how Intune connects to Microsoft Defender for Endpoint.",
    ),
    _article(
        _TENANT,
        "Microsoft 365 Security Architecture: how everything connects",
        "10/24/2026",
        "https://www.linkedin.com/posts/anuradha-kumari51_microsoft365-microsoftentraid-microsoftintune-share-7518584894944600064-36To/",
        "https://learn.microsoft.com/en-us/security/zero-trust/zero-trust-identity-device-access-policies-overview",
        "Explain how identity and device access policies fit together.",
    ),
    _article(
        _M365,
        "Microsoft Intune, Device Enrollment: from zero to managed device",
        "10/1/2026",
        "https://www.linkedin.com/posts/priyam-srivastava-135397182_microsoftintune-intune-microsoft365-share-7510611319218208770-QCuw",
        "https://learn.microsoft.com/en-us/intune/device-enrollment/guide",
        "Explain how a device is enrolled in Microsoft Intune.",
    ),
    _article(
        _M365,
        "Microsoft Intune Device Management and Security",
        "10/5/2026",
        "https://www.linkedin.com/posts/khatri-m-husen-3a8350140_microsoftintune-intune-microsoft365-share-7511527021936553984-utON/",
        "https://learn.microsoft.com/en-us/intune/device-security/overview",
        "Explain how Intune protects devices and data.",
    ),
    _article(
        _M365,
        "Entra ID integration with Microsoft Intune",
        "10/7/2026",
        "https://www.linkedin.com/posts/shankar-kumar-sony_shankarkumarsony-microsoftintune-intune-share-7511530377832996864-WIK7/",
        "https://learn.microsoft.com/en-us/intune/fundamentals/what-is-intune",
        "Explain how Intune uses Microsoft Entra ID.",
    ),
    _article(
        _M365,
        "Microsoft 365 vs Microsoft Entra ID",
        "10/19/2026",
        "https://www.linkedin.com/posts/anuradha-kumari51_microsoft-microsoft-how-share-7517355782510768129-ynCA/",
        "https://learn.microsoft.com/en-us/microsoft-365/enterprise/deploy-identity-solution-overview",
        "Explain how Microsoft 365 uses a cloud identity.",
    ),
    _article(
        _PRIVILEGED,
        "What is Privileged Identity Management?",
        "",
        "",
        "https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-management/pim-configure",
        "Explain what Privileged Identity Management does.",
    ),
    _article(
        _PRIVILEGED,
        "What are access reviews?",
        "",
        "",
        "https://learn.microsoft.com/en-us/entra/id-governance/access-reviews-overview",
        "Explain what access reviews are for.",
    ),
    _article(
        _PRIVILEGED,
        "What is entitlement management?",
        "",
        "",
        "https://learn.microsoft.com/en-us/entra/id-governance/entitlement-management-overview",
        "Explain what entitlement management does.",
    ),
    _article(
        _GUESTS,
        "What is single sign-on in Microsoft Entra ID?",
        "",
        "",
        "https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/what-is-single-sign-on",
        "Explain how single sign-on works in Microsoft Entra ID.",
    ),
    _article(
        _GUESTS,
        "Microsoft Entra B2B best practices",
        "",
        "",
        "https://learn.microsoft.com/en-us/entra/external-id/b2b-fundamentals",
        "Explain the recommended practices for guest users.",
    ),
    _article(
        _GUESTS,
        "Plan a B2B collaboration deployment",
        "",
        "",
        "https://learn.microsoft.com/en-us/entra/architecture/secure-external-access-resources",
        "Explain how to plan collaboration with guest users.",
    ),
    _article(
        _DEVICES,
        "Overview of Windows Autopilot",
        "",
        "",
        "https://learn.microsoft.com/en-us/autopilot/overview",
        "Explain how Windows Autopilot prepares a new device.",
    ),
    _article(
        _DEVICES,
        "Require device compliance with Conditional Access",
        "",
        "",
        "https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-all-users-device-compliance",
        "Explain how Conditional Access can require a compliant device.",
    ),
    _article(
        _DEVICES,
        "Create and deploy app protection policies",
        "",
        "",
        "https://learn.microsoft.com/en-us/intune/app-management/protection/create-policy",
        "Explain how app protection policies protect work data.",
    ),
    _article(
        _DATA,
        "Learn about data loss prevention",
        "",
        "",
        "https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp",
        "Explain how data loss prevention protects sensitive information.",
    ),
    _article(
        _DATA,
        "Learn about retention policies and labels",
        "",
        "",
        "https://learn.microsoft.com/en-us/purview/retention",
        "Explain how retention policies keep or delete content.",
    ),
    _article(
        _DATA,
        "Create and deploy a data loss prevention policy",
        "",
        "",
        "https://learn.microsoft.com/en-us/purview/dlp-create-deploy-policy",
        "Explain how to create a data loss prevention policy.",
    ),
    _goal(
        _IAM,
        "One IAM tool can start your career (IAM tools and Entra ID)",
        "9/23/2026",
        "https://www.linkedin.com/posts/iam-identityaccessmanagement-entraid-share-7507659728177623040-zKF9",
    ),
    _goal(
        _IAM,
        "AskMeIAM: what each level of an IAM career looks like",
        "9/29/2026",
        "https://www.linkedin.com/posts/askmeiam-iam-identityandaccessmanagement-share-7510568909192912896-kact",
    ),
    _goal(
        _IAM,
        "Know the IAM tools. Understand the problems they solve",
        "9/30/2026",
        "https://www.linkedin.com/posts/iam-identityandaccessmanagement-cybersecurity-share-7510929696453361664-BwUm",
    ),
    _goal(
        _IAM,
        "IAM Career Roadmap: Foundations to Automation (AskMeIAM)",
        "9/30/2026",
        "https://www.linkedin.com/posts/iam-identityaccessmanagement-entraid-share-7501488413020254208-2FxN",
    ),
    _goal(
        _IAM,
        "AskMeIAM Training House: Build your IAM skills (Entra ID)",
        "10/10/2026",
        "https://www.linkedin.com/posts/askmeiam-iamtraining-microsoftentraid-share-7514550456120156160-V43L/",
    ),
    _goal(
        _SECURITY,
        "AskMeIAM: your IAM career grows one concept at a time (identity security)",
        "10/17/2026",
        "https://www.linkedin.com/posts/askmeiam-iam-identitysecurity-share-7517049202884079616-EMKM/",
    ),
    _goal(
        _SECURITY,
        "AskMeIAM: your IAM career grows with every problem you solve",
        "10/21/2026",
        "https://www.linkedin.com/posts/pavankumar-pasula_askmeiam-iam-identitysecurity-share-7517801054525370369-7MZ3/",
    ),
    _goal(
        _SECURITY,
        "AskMeIAM: 10 hands-on areas to practise IAM (Entra ID, Okta, SailPoint, CyberArk)",
        "10/23/2026",
        "https://www.linkedin.com/posts/askmeiam-iam-identitysecurity-share-7519269291347619840-LFDA/",
    ),
    _goal(
        _TENANT,
        "Microsoft 365 Administration: Key Areas and Skills",
        "10/18/2026",
        "https://www.linkedin.com/posts/rabialamnyc_activedirectory-microsoftentraid-office365-share-7515246097351557120-zXEC/",
    ),
    _goal(
        _TENANT,
        "Microsoft 365, October 2026 Updates: what IT admins need to know",
        "10/22/2026",
        "https://www.linkedin.com/posts/mgrajendra_microsoft365-m365admin-microsoftcopilot-share-7517840975034007552-hwOY/",
    ),
    _goal(
        _M365,
        "Turning Microsoft 365 into a pencil sketch",
        "9/29/2026",
        "https://www.linkedin.com/posts/deepak-kumar--techstories_microsoft365-microsoft-m365-share-7510193897600516096-NsEM",
    ),
    _goal(
        _M365,
        "Azure, cloud computing and Microsoft 365",
        "10/20/2026",
        "https://www.linkedin.com/posts/nadeemkhan4466_azure-cloudcomputing-microsoft365-share-7516024583058092032-8C6a/",
    ),
)


NO_PAGE_MATCH = "The list does not have that topic yet."


def article_links() -> tuple[SampleLink, ...]:
    """Return the posts that pair with a Microsoft Learn page."""
    return tuple(item for item in SAMPLE_LINKS if item.role == "article")


def find_articles(query: str) -> tuple[SampleLink, ...]:
    """Return starter articles whose title or goal contains the typed words.

    An empty box matches nothing. Reading goals are left out because they have
    no page to open. Capital letters and extra spaces are ignored.
    """
    needle = " ".join(query.casefold().split())
    if not needle:
        return ()
    matched: list[SampleLink] = []
    for item in article_links():
        title = " ".join(item.title.casefold().split())
        goal = " ".join(item.goal.casefold().split())
        if needle in title or needle in goal:
            matched.append(item)
    return tuple(matched)


def reading_goals() -> tuple[SampleLink, ...]:
    """Return the posts that stay study goals."""
    return tuple(item for item in SAMPLE_LINKS if item.role == "goal")


def choice_label(item: SampleLink) -> str:
    """Return the chooser text for one post."""
    return f"{item.group}: {item.title}"


def article_by_label(label: str) -> SampleLink:
    """Return the article whose chooser text matches."""
    return next(item for item in article_links() if choice_label(item) == label)


def goal_by_label(label: str) -> SampleLink:
    """Return the reading goal whose chooser text matches."""
    return next(item for item in reading_goals() if choice_label(item) == label)
