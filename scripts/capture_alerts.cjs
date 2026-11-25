const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
 const deadline=Date.now()+15*60*1000;
 while(Date.now()<deadline){
  const alerts=(await (await fetch('http://localhost:9090/api/v1/alerts')).json()).data.alerts;
  if(alerts.filter(a=>a.state==='firing').length>=2){
   const browser=await chromium.launch({channel:'msedge',headless:true});
   const page=await browser.newPage({viewport:{width:1600,height:1100}});
   await page.goto('http://localhost:9090/alerts',{waitUntil:'domcontentloaded'});
   await page.waitForTimeout(2000);
   await page.screenshot({path:'screenshots/prometheus-alert-firing.png',fullPage:true});
   console.log((await page.locator('body').innerText()).slice(0,4000));
   await browser.close();return;
  }
  await new Promise(r=>setTimeout(r,5000));
 }
 throw new Error('Timed out waiting for two firing alerts');
})().catch(e=>{console.error(e);process.exit(1)});
