/** Real product capture. Uses an isolated headless profile and the repository demo adapter only. */
import puppeteer from 'puppeteer-core';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const executablePath=process.env.CHROME_PATH || (process.platform==='win32'?'C:/Program Files/Google/Chrome/Application/chrome.exe':'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
const browser=await puppeteer.launch({executablePath,headless:true,args:['--disable-gpu','--font-render-hinting=none']});
const page=await browser.newPage();
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const shot=async(file,opts={})=>page.screenshot({path:path.join(root,file),...opts});
try{
  await fs.mkdir(path.join(root,'out/qa'),{recursive:true});
  if(process.argv.includes('--style-only')){
    await page.setViewport({width:1920,height:1080,deviceScaleFactor:1});
    await page.goto(pathToFileURL(path.join(root,'styleframes.html')).href); await page.evaluate(()=>document.fonts.ready); await sleep(600);
    for(const id of ['hero','profiles','launch'])await (await page.$('#'+id)).screenshot({path:path.join(root,`out/qa/style-${id}.png`)});
    console.log('Styleframes captured.');
  }else{
    const base=process.env.PREVIEW_URL||'http://127.0.0.1:19213';
    const layout={source:'Product production UI with isolated public fictional preview adapter',viewport:{w:1920,h:1080},captures:{}};
    await page.setViewport({width:320,height:390,deviceScaleFactor:4});
    await page.goto(base+'/popup.html?window=1'); await page.waitForSelector('.store-row'); await page.evaluate(()=>document.fonts.ready); await sleep(600);
    layout.captures.popup=await page.evaluate(()=>({pageH:document.documentElement.scrollHeight,rows:[...document.querySelectorAll('.store-row')].map(e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height,text:e.textContent}}),search:(()=>{const r=document.querySelector('.search-wrap').getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height}})()}));
    await shot('public/textures/popup-all.png');
    await (await page.$('.store-row')).screenshot({path:path.join(root,'public/textures/popup-row.png')});
    await (await page.$('.search-wrap')).screenshot({path:path.join(root,'public/textures/search.png')});
    for(const [name,value]of [['popup-jing','京'],['popup-jd','京东'],['popup-filter','京东POP']]){await page.$eval('#search',(el,v)=>{el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}))},value);await sleep(600);await shot(`public/textures/${name}.png`);}
    await page.setViewport({width:1920,height:1080,deviceScaleFactor:2});
    await page.goto(base+'/manage.html');await page.waitForSelector('.shop-card');await page.evaluate(()=>document.fonts.ready);await sleep(600);
    layout.captures.manage=await page.evaluate(()=>({pageH:document.documentElement.scrollHeight,cards:[...document.querySelectorAll('.shop-card')].map(e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height,text:e.textContent}}),panel:(()=>{const r=document.querySelector('.profile-panel').getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height}})()}));
    await shot('public/textures/manage-full.png',{fullPage:true});
    const cards=await page.$$('.shop-card');for(let i=0;i<cards.length;i++)await cards[i].screenshot({path:path.join(root,`public/textures/shop-${i}.png`)});
    await (await page.$('.profile-panel')).screenshot({path:path.join(root,'public/textures/profile-panel.png')});
    await page.setViewport({width:1920,height:1080,deviceScaleFactor:4});
    await cards[1].screenshot({path:path.join(root,'public/textures/shop-1-hires.png')});
    await page.setViewport({width:1920,height:1080,deviceScaleFactor:2});
    await page.setContent(`<style>html,body{margin:0;width:1920px;height:1080px;background:#f5f7f6}iframe{position:absolute;left:1170px;top:240px;width:320px;height:390px;border:1px solid #dfe6e2;border-radius:12px;box-shadow:0 20px 65px #163d3420}</style><iframe src="${base}/popup.html?window=1"></iframe>`);
    await sleep(900); await shot('public/textures/hero-stage.png');
    layout.captures.hero={pageH:1080,popup:{x:1170,y:240,w:320,h:390}};
    await fs.writeFile(path.join(root,'public/textures/layout.json'),JSON.stringify(layout,null,2));
    console.log(JSON.stringify(layout,null,2));
  }
}finally{await browser.close()}
