const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const evidence=require('../reports/trace-evidence.json');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 for(const kind of ['slow','error']){
 const page=await browser.newPage({viewport:{width:1600,height:1100}});
 await page.goto('http://localhost:16686/trace/'+evidence[kind].trace_id,{waitUntil:'domcontentloaded'});
 await page.waitForTimeout(3000);
 if(kind==='error'){ await page.locator('a.span-name').filter({hasText:'chat mock-llm-small'}).click(); await page.waitForTimeout(700); await page.getByRole('tab',{name:'Details',exact:true}).click(); await page.waitForTimeout(500); console.log('expanded',(await page.locator('body').innerText()).slice(-5000)); }
 console.log(kind,(await page.locator('body').innerText()).slice(0,3000));
 await page.screenshot({path:'screenshots/jaeger-'+kind+'-trace.png',fullPage:true});
 await page.close();
 }
 await browser.close();
})();
