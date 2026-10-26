# Build 10 — Starter catalog

The picture is [10-starter-catalog-diagram.png](10-starter-catalog-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The home page, the reader, and the study pack already work. This build adds the 37 LinkedIn posts as a catalog on that page.

## What this build does

`studymaster/sample_links.py` holds the 37 posts. Each post keeps its group, title, date, and LinkedIn address.

- 25 posts are articles. Each one also has one public Microsoft Learn URL. Choosing it fills **Page link** with that Learn URL and fills **Goal** with one short sentence. The learner still presses **Study this page**. The reader fetches the Learn page only.
- 12 posts are reading goals. Choosing one fills **Goal** only. The LinkedIn address stays on the screen as a reference. It is not fetched, and it is not sent to the lab or runbook.
- Picking a catalog item does not call OpenAI. The paid call still happens only when the learner presses **Study this page**, **Rewrite**, or **Check my answer**.

The title stays **StudyMaster AI**.

## Page behavior

Above the form, the page shows two choosers:

1. **Starter article.** The first choice is "Paste my own link". The other choices are the 25 articles, labeled with the group and the title. Changing the choice writes the Learn URL into **Page link** and the short goal into **Goal**.
2. **Reading goal.** The first choice is "No reading goal". The other choices are the 12 goals. Changing the choice writes the goal sentence into **Goal** and leaves **Page link** unchanged. A caption says: "This is a study goal. Paste a public page before you press Study this page."

The LinkedIn address for the current choice is shown as plain text. It is not a fetch button.

The existing form, history, download, rewrite, and grader stay as they are.

## Catalog data

Each item has: group, title, date, LinkedIn URL, role (`article` or `goal`), Learn URL, and goal sentence.

Rules the tests will lock in:

- There are 37 items: 25 articles and 12 goals.
- Every article Learn URL starts with `https://learn.microsoft.com/`.
- Every goal has an empty Learn URL.
- No Learn URL contains `linkedin.com`.
- The 37 LinkedIn URLs are unique.
- Two articles share one Learn page, because both posts are the Active Directory versus Microsoft Entra ID comparison. Every other article has its own Learn page.
- Tests check the strings only. They do not open Microsoft Learn or call OpenAI.

These Learn URLs were checked on October 25, 2026. Each one answered as a public page.

### IAM articles

| Title | Learn page | Goal sentence |
| --- | --- | --- |
| Microsoft Entra ID / Azure AD in IAM | `https://learn.microsoft.com/en-us/entra/fundamentals/whatis` | Explain what Microsoft Entra ID does. |
| Active Directory and Windows Server in IAM | `https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/active-directory-domain-services-overview` | Explain what Active Directory Domain Services does. |
| Active Directory / Windows Server for system administration | `https://learn.microsoft.com/en-us/windows-server/administration/server-manager/server-manager` | Describe how Server Manager is used to administer Windows Server. |
| On-Premises Active Directory vs. Microsoft Entra ID | `https://learn.microsoft.com/en-us/entra/fundamentals/compare` | Compare on-premises Active Directory with Microsoft Entra ID. |
| Creating an Active Directory user is only the beginning | `https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage-user-accounts-in-windows-server` | Describe how to create and manage an Active Directory user. |
| Active Directory / Windows Server / IT infrastructure | `https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/forest-design-models` | Explain how an Active Directory forest is designed. |
| RBAC Implementation: Managing Access vs Creating Roles | `https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/concept-understand-roles` | Explain how Microsoft Entra roles control access. |
| Active Directory Authentication in Windows Server Explained | `https://learn.microsoft.com/en-us/windows-server/security/windows-authentication/windows-authentication-overview` | Explain how Windows authentication works. |
| Active Directory vs. Microsoft Entra ID: Key Differences | `https://learn.microsoft.com/en-us/entra/fundamentals/compare` | Compare on-premises Active Directory with Microsoft Entra ID. |

### IAM Security articles

| Title | Learn page | Goal sentence |
| --- | --- | --- |
| Microsoft Entra ID MFA (IAM) | `https://learn.microsoft.com/en-us/entra/identity/authentication/concept-mfa-howitworks` | Explain how Microsoft Entra multifactor authentication works. |
| Conditional Access: what if knowing the identity is not enough? | `https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview` | Explain what Conditional Access checks before it allows a sign-in. |
| Zero Trust, cybersecurity and identity security | `https://learn.microsoft.com/en-us/security/zero-trust/deploy/identity` | Explain the identity part of Zero Trust. |
| Authentication Methods in Microsoft Entra ID | `https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-methods` | Explain the authentication methods in Microsoft Entra ID. |
| Microsoft Entra Connect Sync: important change by April 7, 2027 | `https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/harden-update-ad-fs-pingfederate` | Explain the Entra Connect Sync upgrade required by April 7, 2027. |

### Microsoft 365 Tenant articles

| Title | Learn page | Goal sentence |
| --- | --- | --- |
| Microsoft 365 Admin Routine: Security, Productivity and Compliance | `https://learn.microsoft.com/en-us/microsoft-365/admin/admin-overview/admin-center-overview` | Explain what the Microsoft 365 admin center is for. |
| Microsoft Purview, Information Protection Architecture | `https://learn.microsoft.com/en-us/purview/information-protection` | Explain what Microsoft Purview Information Protection does. |
| Microsoft 365 Tenant Architecture | `https://learn.microsoft.com/en-us/microsoft-365/solutions/tenant-management-tenants` | Explain what a Microsoft 365 tenant is. |
| How to Sync / Migrate Active Directory Objects to Microsoft Entra ID | `https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-sync-whatis` | Explain how Entra Connect Sync moves Active Directory objects to Microsoft Entra ID. |
| Microsoft 365 Employee Offboarding: do more than delete the user | `https://learn.microsoft.com/en-us/microsoft-365/admin/add-users/remove-former-employee` | Explain the steps for removing a former employee from Microsoft 365. |
| Microsoft 365, Intune, Defender Integration for IT Management | `https://learn.microsoft.com/en-us/intune/device-security/microsoft-defender/configure-integration` | Explain how Intune connects to Microsoft Defender for Endpoint. |
| Microsoft 365 Security Architecture: how everything connects | `https://learn.microsoft.com/en-us/security/zero-trust/zero-trust-identity-device-access-policies-overview` | Explain how identity and device access policies fit together. |

### Microsoft 365 articles

| Title | Learn page | Goal sentence |
| --- | --- | --- |
| Microsoft Intune, Device Enrollment: from zero to managed device | `https://learn.microsoft.com/en-us/intune/device-enrollment/guide` | Explain how a device is enrolled in Microsoft Intune. |
| Microsoft Intune Device Management and Security | `https://learn.microsoft.com/en-us/intune/device-security/overview` | Explain how Intune protects devices and data. |
| Entra ID integration with Microsoft Intune | `https://learn.microsoft.com/en-us/intune/fundamentals/what-is-intune` | Explain how Intune uses Microsoft Entra ID. |
| Microsoft 365 vs Microsoft Entra ID | `https://learn.microsoft.com/en-us/microsoft-365/enterprise/deploy-identity-solution-overview` | Explain how Microsoft 365 uses a cloud identity. |

### Reading goals

These twelve stay goals. The goal sentence is the title. The Learn URL is empty.

IAM:

1. One IAM tool can start your career (IAM tools and Entra ID). 9/23/2026. https://www.linkedin.com/posts/iam-identityaccessmanagement-entraid-share-7507659728177623040-zKF9
2. AskMeIAM: what each level of an IAM career looks like. 9/29/2026. https://www.linkedin.com/posts/askmeiam-iam-identityandaccessmanagement-share-7510568909192912896-kact
3. Know the IAM tools. Understand the problems they solve. 9/30/2026. https://www.linkedin.com/posts/iam-identityandaccessmanagement-cybersecurity-share-7510929696453361664-BwUm
4. IAM Career Roadmap: Foundations to Automation (AskMeIAM). 9/30/2026. https://www.linkedin.com/posts/iam-identityaccessmanagement-entraid-share-7501488413020254208-2FxN
5. AskMeIAM Training House: Build your IAM skills (Entra ID). 10/10/2026. https://www.linkedin.com/posts/askmeiam-iamtraining-microsoftentraid-share-7514550456120156160-V43L/

IAM Security:

1. AskMeIAM: your IAM career grows one concept at a time (identity security). 10/17/2026. https://www.linkedin.com/posts/askmeiam-iam-identitysecurity-share-7517049202884079616-EMKM/
2. AskMeIAM: your IAM career grows with every problem you solve. 10/21/2026. https://www.linkedin.com/posts/pavankumar-pasula_askmeiam-iam-identitysecurity-share-7517801054525370369-7MZ3/
3. AskMeIAM: 10 hands-on areas to practise IAM (Entra ID, Okta, SailPoint, CyberArk). 10/23/2026. https://www.linkedin.com/posts/askmeiam-iam-identitysecurity-share-7519269291347619840-LFDA/

Microsoft 365 Tenant:

1. Microsoft 365 Administration: Key Areas and Skills. 10/18/2026. https://www.linkedin.com/posts/rabialamnyc_activedirectory-microsoftentraid-office365-share-7515246097351557120-zXEC/
2. Microsoft 365, October 2026 Updates: what IT admins need to know. 10/22/2026. https://www.linkedin.com/posts/mgrajendra_microsoft365-m365admin-microsoftcopilot-share-7517840975034007552-hwOY/

Microsoft 365:

1. Turning Microsoft 365 into a pencil sketch. 9/29/2026. https://www.linkedin.com/posts/deepak-kumar--techstories_microsoft365-microsoft-m365-share-7510193897600516096-NsEM
2. Azure, cloud computing and Microsoft 365. 10/20/2026. https://www.linkedin.com/posts/nadeemkhan4466_azure-cloudcomputing-microsoft365-share-7516024583058092032-8C6a/

The article rows above keep the same LinkedIn addresses and dates already listed in `01-studymaster-agent.md`. The code copies those addresses onto the article items. The code does not pass any LinkedIn address to the reader.

## Tests

`tests/test_sample_links.py` checks the counts, the Learn URL rule, the empty goal URLs, and the unique LinkedIn addresses.

`tests/test_home.py` checks that the two choosers appear, that choosing an article shows its Learn URL in **Page link**, and that the model is not called by the choice itself.

## Later catalogs

These four catalogs are written here and are not part of this build's code. After the 37 posts work on the page, each one gets its own numbered plan file and picture, then its own confirmation, before any of its code is written. Each article is a public Microsoft Learn page. A choice fills **Page link** and **Goal**. The reader does not open LinkedIn. These pages were found on October 25, 2026. Each build rechecks its own URLs on the day its plan file is written.

Build 11 — Privileged access and identity governance:

- What is Privileged Identity Management: `https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-management/pim-configure`
- What are access reviews: `https://learn.microsoft.com/en-us/entra/id-governance/access-reviews-overview`
- What is entitlement management: `https://learn.microsoft.com/en-us/entra/id-governance/entitlement-management-overview`

Build 12 — Apps and guest access:

- What is single sign-on in Microsoft Entra ID: `https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/what-is-single-sign-on`
- Microsoft Entra B2B best practices: `https://learn.microsoft.com/en-us/entra/external-id/b2b-fundamentals`
- Plan a B2B collaboration deployment: `https://learn.microsoft.com/en-us/entra/architecture/secure-external-access-resources`

Build 13 — Devices after enrollment:

- Overview of Windows Autopilot: `https://learn.microsoft.com/en-us/autopilot/overview`
- Require device compliance with Conditional Access: `https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-all-users-device-compliance`
- Create and deploy app protection policies: `https://learn.microsoft.com/en-us/intune/app-management/protection/create-policy`

Build 14 — Data protection:

- Learn about data loss prevention: `https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp`
- Learn about retention policies and labels: `https://learn.microsoft.com/en-us/purview/retention`
- Create and deploy a data loss prevention policy: `https://learn.microsoft.com/en-us/purview/dlp-create-deploy-policy`

## Left alone

The reader still refuses private addresses. The agents still use only the fetched page. A local free model stays optional. The real `.env` file stays out of git.
