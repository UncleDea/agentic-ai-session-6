# Build 34 — One public page

The picture is [34-web-page-diagram.png](34-web-page-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The finder still starts with the starter list.

## What this build does

**Find a page** looks through the starter articles first. One match and several matches stay the same.

When the list has no match, the page says **The list does not have that topic yet.** It then looks for one public `https` address. A safe address is shown with **Use this page**. That button fills **Page link** only. **Study this page** is still the button that reads the page and calls the model.

An address that is not public `https` is left out. When no safe address comes back, the page says **No public page was found.**

## Left alone

The three checks stay. The title stays **StudyMaster AI**. The study agents still read only the page in **Page link**.
