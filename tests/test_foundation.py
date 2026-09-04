from pylenium import Browser

def test_browser_launch():
    print("Launching browser...")
    browser = Browser.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com")
    title = page.title()
    print(f"Title: {title}")
    assert "Example Domain" in title
    browser.close()
    print("Success!")

if __name__ == "__main__":
    test_browser_launch()
