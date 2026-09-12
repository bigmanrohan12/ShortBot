await page.goto('https://www.youtube.com');

const searchBox = page.getByRole('combobox');

await searchBox.fill('Young Sheldon');

const searchButton = page.getByRole('button', {
  name: 'Search',
  description: 'Search'
});

await searchButton.click();

await page.waitForTimeout(3000);

const shortsLinks = await page.locator('a[href*="/shorts/"]').all();

const results = [];
const seen = new Set();

for (const link of shortsLinks) {
  const url = await link.getAttribute('href');
  const title = await link.getAttribute('title');

  // Ignore navigation links and elements without a real title
  if (!url || url === '/shorts/' || !title) {
    continue;
  }

  // Ignore duplicate URLs
  if (seen.has(url)) {
    continue;
  }

  seen.add(url);

  results.push({
    title: title,
    url: 'https://www.youtube.com' + url
  });
}

return results;