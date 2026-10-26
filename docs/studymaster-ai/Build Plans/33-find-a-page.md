# Build 33 — Find a page

The picture is [33-find-a-page-diagram.png](33-find-a-page-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The finder fills the form from the starter list.

## What this build does

A box above the form asks **What do you want to learn?** **Find a page** sends those words with the click and looks through the starter articles.

One match fills **Page link** with that article's Microsoft Learn address and **Goal** with its goal sentence. Several matches show the titles, and the one you pick fills the form the same way. No match says **The list does not have that topic yet.**

The LinkedIn line stays a reference and is not opened. This build does not call OpenAI. **Study this page** is still the button that reads the page. **Start over** also clears **What do you want to learn?**

## Left alone

A search of the public web waits for a later build. The three checks stay. The title stays **StudyMaster AI**.
