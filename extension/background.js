const latoUrl = browser.runtime.getURL("index.html");

browser.action.onClicked.addListener(async () => {
  const tabs = await browser.tabs.query({ url: latoUrl });
  if (tabs[0]?.id) {
    await browser.tabs.update(tabs[0].id, { active: true });
    if (tabs[0].windowId) await browser.windows.update(tabs[0].windowId, { focused: true });
    return;
  }
  await browser.tabs.create({ url: latoUrl });
});
