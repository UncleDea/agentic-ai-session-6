"""Tests for the starter catalog.

These tests check the saved strings. They do not open Microsoft Learn,
LinkedIn, or OpenAI.
"""

from collections import Counter

from studymaster.sample_links import (
    SAMPLE_LINKS,
    article_links,
    find_articles,
    reading_goals,
)

SHARED_LEARN_URL = "https://learn.microsoft.com/en-us/entra/fundamentals/compare"


def test_catalog_counts():
    assert len(SAMPLE_LINKS) == 49
    assert len(article_links()) == 37
    assert len(reading_goals()) == 12


def test_article_learn_urls_are_public_learn_pages():
    urls = [item.learn_url for item in article_links()]
    assert all(url.startswith("https://learn.microsoft.com/") for url in urls)
    assert all("linkedin.com" not in url for url in urls)
    shared = [url for url, count in Counter(urls).items() if count > 1]
    assert shared == [SHARED_LEARN_URL]


def test_reading_goals_have_no_learn_page():
    assert reading_goals()
    assert all(item.learn_url == "" for item in reading_goals())
    assert all(item.goal == item.title for item in reading_goals())
    assert all(item.role == "goal" for item in reading_goals())


def test_linkedin_addresses_are_unique_references():
    urls = [item.linkedin_url for item in SAMPLE_LINKS if item.linkedin_url]
    assert len(urls) == 37
    assert len(urls) == len(set(urls))
    assert all(url.startswith("https://www.linkedin.com/posts/") for url in urls)


def test_privileged_access_articles_use_learn_pages_only():
    items = [item for item in article_links() if item.group == "Privileged access"]
    assert [item.title for item in items] == [
        "What is Privileged Identity Management?",
        "What are access reviews?",
        "What is entitlement management?",
    ]
    assert [item.learn_url for item in items] == [
        "https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-management/pim-configure",
        "https://learn.microsoft.com/en-us/entra/id-governance/access-reviews-overview",
        "https://learn.microsoft.com/en-us/entra/id-governance/entitlement-management-overview",
    ]
    assert all(item.linkedin_url == "" for item in items)
    assert all(item.goal for item in items)


def test_apps_and_guests_articles_use_learn_pages_only():
    items = [item for item in article_links() if item.group == "Apps and guests"]
    assert [item.title for item in items] == [
        "What is single sign-on in Microsoft Entra ID?",
        "Microsoft Entra B2B best practices",
        "Plan a B2B collaboration deployment",
    ]
    assert [item.learn_url for item in items] == [
        "https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/what-is-single-sign-on",
        "https://learn.microsoft.com/en-us/entra/external-id/b2b-fundamentals",
        "https://learn.microsoft.com/en-us/entra/architecture/secure-external-access-resources",
    ]
    assert all(item.linkedin_url == "" for item in items)
    assert all(item.goal for item in items)


def test_devices_articles_use_learn_pages_only():
    items = [item for item in article_links() if item.group == "Devices"]
    assert [item.title for item in items] == [
        "Overview of Windows Autopilot",
        "Require device compliance with Conditional Access",
        "Create and deploy app protection policies",
    ]
    assert [item.learn_url for item in items] == [
        "https://learn.microsoft.com/en-us/autopilot/overview",
        "https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-all-users-device-compliance",
        "https://learn.microsoft.com/en-us/intune/app-management/protection/create-policy",
    ]
    assert all(item.linkedin_url == "" for item in items)
    assert all(item.goal for item in items)


def test_data_protection_articles_use_learn_pages_only():
    items = [item for item in article_links() if item.group == "Data protection"]
    assert [item.title for item in items] == [
        "Learn about data loss prevention",
        "Learn about retention policies and labels",
        "Create and deploy a data loss prevention policy",
    ]
    assert [item.learn_url for item in items] == [
        "https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp",
        "https://learn.microsoft.com/en-us/purview/retention",
        "https://learn.microsoft.com/en-us/purview/dlp-create-deploy-policy",
    ]
    assert all(item.linkedin_url == "" for item in items)
    assert all(item.goal for item in items)


def test_find_articles_matches_title_words_and_skips_reading_goals():
    one = find_articles("  Learn about data loss prevention ")
    assert [item.title for item in one] == ["Learn about data loss prevention"]
    assert one[0].learn_url == "https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp"
    several = find_articles("data loss prevention")
    assert [item.title for item in several] == [
        "Learn about data loss prevention",
        "Create and deploy a data loss prevention policy",
    ]
    assert find_articles("underwater basket weaving") == ()
    assert find_articles("   ") == ()
    assert all(item.role == "article" for item in find_articles("entra"))
