"""Start the StudyMaster AI website.

This file is the front door. Streamlit runs it, and it asks the user
interface module to draw the page.

From the project folder:

    streamlit run app.py
"""

from studymaster.ui.home import main

main()
