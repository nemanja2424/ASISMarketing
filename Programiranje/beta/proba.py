from camoufox import Camoufox

with Camoufox() as browser:
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://browserleaks.com")

    print("Camoufox radi. CTRL+C za izlaz.")
    input()
