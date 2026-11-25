const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1600,height:1200}});
 await page.goto(process.argv[2],{waitUntil:'domcontentloaded',timeout:60000});
 await page.waitForTimeout(7000);
 await page.screenshot({path:process.argv[3],fullPage:true});
 console.log((await page.locator('body').innerText()).slice(0,1500));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
