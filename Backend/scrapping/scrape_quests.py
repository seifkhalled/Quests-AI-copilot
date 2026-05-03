import asyncio
import csv
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Replace with the actual URL
        url = "https://code-quests.com/quests/"
        await page.goto(url)

        # Wait for the grid container to be visible
        await page.wait_for_selector(".cq-grid")

        # Select all quest cards
        cards = await page.query_selector_all(".cq-card")
        
        quest_data = []

        for card in cards:
            # Extract the title and the link
            # We use the title link specifically
            title_element = await card.query_selector(".cq-card-title a")
            
            if title_element:
                title = await title_element.inner_text()
                # .get_attribute("href") returns the relative link, 
                # but we can use page.evaluate to get the absolute URL easily
                href = await title_element.get_attribute("href")
                
                # Construct absolute URL if it's relative
                if href.startswith("?"):
                    base_url = url.split('?')[0]
                    full_url = f"{base_url}{href}"
                else:
                    full_url = href

                quest_data.append({
                    "Quest Title": title.strip(),
                    "URL": full_url
                })

        # Save to CSV
        with open("quests.csv", mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Quest Title", "URL"])
            writer.writeheader()
            writer.writerows(quest_data)

        print(f"✅ Successfully scraped {len(quest_data)} quests into 'quests.csv'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())