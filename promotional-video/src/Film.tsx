import React from 'react';
import {AbsoluteFill,Audio,Img,Sequence,Easing,interpolate,staticFile,useCurrentFrame} from 'remotion';
import {PageCam,CamKey} from './lib/PageCam';
import layout from '../public/textures/layout.json';

// Spotlight / finale are adapted from video-shotcraft, Copyright 2026 Wei Yihao,
// Apache-2.0. See THIRD_PARTY_NOTICES.md and references/video-shotcraft-LICENSE.txt.
// Changed: product textures, palette, typography, framing, timing and narrative.
const C={bg:'#f5f7f6',ink:'#24322e',green:'#235c50',dark:'#163d34',muted:'#66746e',line:'#dfe6e2',tint:'#e8f0ec'};
const FONT='"Segoe UI","Microsoft YaHei",sans-serif';
const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const ease=Easing.bezier(.25,.46,.45,.94);
const pop=Easing.bezier(.2,1.25,.3,1);
const fly=Easing.bezier(.34,1.4,.44,1);
const v=(f:number,range:number[],values:number[],e=(x:number)=>x)=>interpolate(f,range,values,{...clamp,easing:e});
const tex=(s:string)=>staticFile('textures/'+s);
export const SHOTS={hero:{from:0,duration:150},search:{from:150,duration:180},bind:{from:330,duration:150},map:{from:480,duration:180},native:{from:660,duration:120},outro:{from:780,duration:180}};

const Brand:React.FC<{dark?:boolean}>=({dark=false})=><div style={{display:'flex',alignItems:'center',gap:16,fontSize:36,fontWeight:600,color:dark?'#fff':C.ink}}><Img src={staticFile('icon.png')} style={{width:54,height:54}}/>快店快点</div>;
const Header:React.FC<{label:string,dark?:boolean}>=({label,dark=false})=><div style={{position:'absolute',left:96,right:96,top:65,display:'flex',alignItems:'center',justifyContent:'space-between',zIndex:10}}><Brand dark={dark}/><div style={{fontSize:34,color:dark?'#bcd7cc':C.muted,letterSpacing:2}}>{label}</div></div>;
const Small:React.FC<{children:React.ReactNode,dark?:boolean}>=({children,dark=false})=><div style={{position:'absolute',left:110,bottom:52,fontSize:34,color:dark?'#bbd8ca':C.muted,zIndex:20}}>{children}</div>;
const Pointer:React.FC<{x:number,y:number,click?:number}>=({x,y,click=0})=><div style={{position:'absolute',left:x,top:y,zIndex:50,transform:`scale(${1-.12*click})`,transformOrigin:'0 0'}}><svg width="45" height="53" viewBox="0 0 40 48"><path d="M4 2V34L13 27L21 44L28 40L20 24L33 24Z" fill="#1b372c" stroke="white" strokeWidth="3"/></svg></div>;

function Hero(){
 const f=useCurrentFrame();
 // SceneOpen macro shifted to f0: 32f lock, 16f push, 10f rise,54f hover,18f reseat.
 const keys:CamKey[]=[{frame:0,cx:1080,cy:470,zoom:1.45,rotY:0,rotX:0,persp:1500},{frame:32,cx:1080,cy:470,zoom:1.45,rotY:0,rotX:0,persp:1500},{frame:48,cx:1130,cy:435,zoom:1.72,rotY:24,rotX:3,persp:1500},{frame:150,cx:1130,cy:435,zoom:1.72,rotY:24,rotX:3,persp:1500}];
 const rise=v(f,[48,58],[0,1],pop),reseat=v(f,[112,130],[0,1],Easing.bezier(.4,0,.3,1.05)),lift=rise*(1-reseat);
 const z=110*lift+Math.sin((f-58)/40*Math.PI*2)*4*lift;
 const press=v(f,[126,129,130],[1,.997,1]);
 const first=f>=60&&f<=76,second=f>=80&&f<=100;
 const beam=first?v(f,[60,74],[0,1]):v(f,[80,100],[0,1],Easing.bezier(.4,0,.4,1));
 const spotX=v(f,[4,8,16,22,28,48],[45,45,80,58,72,72],ease);
 const spotY=v(f,[4,8,16,22,28,48],[30,30,40,65,60,50],ease);
 const pool=v(f,[22,32,48],[620,420,360],Easing.bezier(.4,0,.3,1))*(1+v(f,[32,36,41],[0,.06,0]));
 const dim=v(f,[22,32,48],[.16,.34,.42]);
 const slotVis=Math.min(1,rise*2)*(1-reseat),landPulse=v(f,[126,130,134],[0,1,0]);
 const slotEdge=Math.min(1,.4*(1-reseat))+.6*landPulse;
 const beamTrail=f>=100?v(f,[100,112],[.35,0]):0;
 return <AbsoluteFill style={{background:C.bg}}>
  <PageCam src="textures/hero-stage.png" pageH={1080} keys={keys} ease={Easing.bezier(.35,0,.2,1)}>
   {slotVis>.02&&<div style={{position:'absolute',left:1168,top:238,width:324,height:394,borderRadius:12,background:C.bg,opacity:slotVis,boxShadow:`inset 0 0 26px rgba(35,92,80,${.12*slotEdge})`}}><div style={{position:'absolute',inset:0,borderRadius:12,border:'1.5px solid #235c50',opacity:slotEdge}}/></div>}
   <div style={{position:'absolute',left:1170,top:240,width:320,height:390,transform:`translateZ(${z}px) scale(${press})`,transformStyle:'preserve-3d',borderRadius:12,boxShadow:`0 ${8*lift}px ${10+12*lift}px #163d3420,0 ${46*lift}px ${90*lift}px #163d3438`}}>
    <div style={{position:'absolute',inset:0,borderRadius:12,overflow:'hidden',background:'#fff'}}><Img src={tex('popup-all.png')} style={{width:'100%',height:'100%'}}/>
    {(first||second)&&lift>.4&&<svg width="320" height="390" viewBox="0 0 320 390" style={{position:'absolute',inset:0,opacity:first?1:.62}}><rect x="2" y="2" width="316" height="386" rx="11" fill="none" stroke="#235c50" strokeWidth={first?5:3.5} pathLength="1" strokeDasharray=".14 1" strokeDashoffset={-beam}/><rect x="2" y="2" width="316" height="386" rx="11" fill="none" stroke="#c3e2d4" strokeWidth={first?2.5:1.75} pathLength="1" strokeDasharray=".14 1" strokeDashoffset={-beam}/></svg>}
    <div style={{position:'absolute',inset:0,background:'linear-gradient(160deg,#ffffff80,transparent 40%)',opacity:lift}}/>
    </div>
    <div style={{position:'absolute',inset:0,borderRadius:12,boxShadow:`inset 0 0 0 1px rgba(255,255,255,${.7*lift})`}}/>
    {(beamTrail>0||landPulse>0)&&<div style={{position:'absolute',inset:-1,borderRadius:13,border:'1.5px solid #235c50',opacity:Math.max(beamTrail,landPulse*.6)}}/>}
   </div>
  </PageCam>
  <AbsoluteFill style={{background:`radial-gradient(${pool}px ${pool*.8}px at ${spotX}% ${spotY}%,rgba(22,61,52,0) 28%,rgba(22,61,52,${dim}) 100%)`,opacity:v(f,[2,10],[0,1])}}/>
  <AbsoluteFill style={{background:'linear-gradient(90deg,#f5f7f6fa,#f5f7f6eb 40%,#f5f7f600 64%)'}}/>
  <Header label="多店铺 · 轻巧入口"/>
  <div style={{position:'absolute',left:110,top:300,opacity:v(f,[0,18],[0,1]),transform:`translateY(${v(f,[0,26],[24,0],ease)}px)`}}>
   <div style={{fontSize:100,fontWeight:650,lineHeight:1.34,letterSpacing:-4}}>后台太多？<br/><span style={{color:C.green}}>一个小窗就够。</span></div>
   <div style={{fontSize:38,color:C.muted,lineHeight:1.7,marginTop:38}}>京东 · 淘宝 / 天猫 · PDD<br/>日常点店名，设置才进管理页。</div>
  </div><Small>实际界面 · 示例数据</Small>
 </AbsoluteFill>;
}

function Search(){
 const f=useCurrentFrame();const x=1120,y=150,w=640,h=780;
 const src=f<45?'popup-all.png':f<60?'popup-jing.png':f<90?'popup-jd.png':'popup-filter.png';
 const px=v(f,[10,30,98,120],[1780,1325,1325,1335],ease),py=v(f,[10,30,98,120],[890,307,307,430],ease);
 const click=f>=126&&f<138?v(f,[126,130,138],[0,1,0]):0;
 return <AbsoluteFill style={{background:C.bg}}>
  <Header label="01 / 快速找到"/>
  <div style={{position:'absolute',left:110,top:280}}><div style={{fontSize:100,fontWeight:650,lineHeight:1.35,letterSpacing:-4}}>找店铺，<br/><span style={{color:C.green}}>不用找头像。</span></div><div style={{fontSize:40,color:C.muted,marginTop:42}}>输入店名，缩小范围。</div>
    <div style={{marginTop:70,padding:'22px 28px',borderLeft:'5px solid '+C.green,background:C.tint,fontSize:38,color:C.green,opacity:v(f,[120,138],[0,1])}}>京东POP → 电商资料 2</div>
  </div>
  <div style={{position:'absolute',left:x,top:y,width:w,height:h,border:'1px solid '+C.line,borderRadius:24,boxShadow:'0 30px 90px #163d3426',overflow:'hidden',background:'#fff',transform:`translateY(${v(f,[0,18],[28,0],ease)}px)`}}><Img src={tex(src)} style={{width:w,height:h}}/>
    {f>=120&&<div style={{position:'absolute',left:14,top:238,width:612,height:72,borderRadius:12,background:'#235c500e',border:'2px solid #235c50',opacity:v(f,[120,126],[0,1])}}/>}
  </div>
  {f>=10&&<Pointer x={px} y={py} click={click}/>}
  <Small>按绑定资料发送打开请求；登录到期仍需正常验证。</Small>
 </AbsoluteFill>;
}

function Bind(){
 const f=useCurrentFrame();const card=layout.captures.manage.cards[1];
 const keys:CamKey[]=[{frame:0,cx:960,cy:560,zoom:.88,rotX:0,rotY:0},{frame:32,cx:960,cy:560,zoom:.88,rotX:0,rotY:0},{frame:65,cx:1022,cy:483.6,zoom:2.4,rotX:0,rotY:0},{frame:150,cx:1022,cy:483.6,zoom:2.4,rotX:0,rotY:0}];
 return <AbsoluteFill style={{background:C.bg}}>
  <div style={{position:'absolute',inset:0}}><PageCam src="textures/manage-full.png" pageH={layout.captures.manage.pageH} keys={keys}>
    <Img src={tex('shop-1-hires.png')} style={{position:'absolute',left:card.x,top:card.y,width:card.w,height:card.h,opacity:v(f,[38,44],[0,1])}}/>
    <div style={{position:'absolute',left:card.x,top:card.y,width:card.w,height:card.h,borderRadius:10,border:'3px solid #235c50',opacity:v(f,[50,65],[0,1]),boxShadow:'0 0 0 5000px #f5f7f621'}}/>
  </PageCam></div>
  <div style={{position:'absolute',top:0,left:0,right:0,height:265,background:'linear-gradient(#f5f7f6 85%,#f5f7f600)'}}/>
  <div style={{position:'absolute',bottom:0,left:0,right:0,height:260,background:'linear-gradient(#f5f7f600,#f5f7f6 28%)'}}/>
  <Header label="02 / 绑定清楚"/>
  <div style={{position:'absolute',top:145,left:110,fontSize:68,fontWeight:650,color:C.green}}>店铺和资料，一一对应。</div>
  <div style={{position:'absolute',left:110,bottom:145,padding:'23px 32px',background:C.green,color:'#fff',fontSize:44,borderRadius:16,opacity:v(f,[78,96],[0,1])}}>京东POP → 电商资料 2 ｜ 沿用该资料的登录状态</div>
  <Small>真实管理页 · 示例数据；首次打开请核对店铺账号。</Small>
 </AbsoluteFill>;
}

function ProfileMap(){
 const f=useCurrentFrame();const p=v(f,[0,22],[0,1],ease);
 return <AbsoluteFill style={{background:C.dark,color:'#fff'}}>
  <Header label="03 / 资料规划示意" dark/>
  <div style={{position:'absolute',left:110,top:190,opacity:p,transform:`translateY(${(1-p)*25}px)`,fontSize:86,fontWeight:650,letterSpacing:-3}}>5 个账号，规划成 <span style={{color:'#bce3cf'}}>3 份资料。</span></div>
  <div style={{position:'absolute',left:110,right:110,top:380,display:'flex',gap:32}}>
   {[['京东账号 A','淘宝账号 A'],['京东账号 B','淘宝账号 B'],['京东账号 C']].map((items,i)=>{const t=v(f,[20+i*6,46+i*6],[0,1],ease);return <div key={i} style={{width:545,height:410,padding:36,background:C.bg,border:'1px solid #bcd5c8',borderRadius:26,color:C.ink,transform:`translateY(${(1-t)*60}px)`,opacity:t}}><div style={{display:'flex',alignItems:'center',gap:20,fontSize:48,fontWeight:650}}><span style={{display:'grid',placeItems:'center',width:56,height:56,borderRadius:28,background:C.green,color:'white',fontSize:32}}>{i+1}</span>电商资料 {i+1}</div>
    {items.map((text,j)=>{const q=v(f,[60+i*9+j*12,80+i*9+j*12],[0,1],ease);return <div key={text} style={{marginTop:24,padding:'19px 22px',background:j?'#f4ece0':C.tint,borderRadius:14,fontSize:40,opacity:q,transform:`translateX(${(1-q)*30}px)`}}><span style={{display:'inline-block',width:10,height:10,borderRadius:5,background:j?'#ae651b':'#b2403d',marginRight:18,verticalAlign:'middle'}}/>{text}</div>})}
   </div>})}
  </div>
  <div style={{position:'absolute',left:110,top:857,fontSize:40,color:'#d1e7dc',opacity:v(f,[115,130],[0,1])}}>不同登录体系可复用，同一体系不同账号分开。</div>
  <Small dark>淘宝与天猫按同一登录体系处理；仅调整入口绑定。</Small>
 </AbsoluteFill>;
}

function Native(){
 const f=useCurrentFrame();return <AbsoluteFill style={{background:C.bg}}>
 <Header label="04 / 保持原来的工作方式"/>
 <div style={{position:'absolute',left:110,top:250,right:110}}><div style={{fontSize:104,lineHeight:1.3,fontWeight:650,letterSpacing:-4,opacity:v(f,[0,20],[0,1]),transform:`translateY(${v(f,[0,26],[30,0],ease)}px)`}}>还是你熟悉的 <span style={{color:C.green}}>Chrome。</span></div>
  <div style={{height:5,width:v(f,[18,45],[0,1700],ease),background:C.green,marginTop:45}}/>
  <div style={{display:'flex',gap:44,marginTop:60}}>{[['原生浏览器','网页、资料、其他扩展照常使用'],['数据留本机','不读取或搬运 Cookie']].map(([title,sub],i)=><div key={title} style={{width:825,opacity:v(f,[35+i*15,56+i*15],[0,1]),transform:`translateY(${v(f,[35+i*15,56+i*15],[24,0],ease)}px)`}}><div style={{fontSize:60,fontWeight:600,marginBottom:24}}>{title}</div><div style={{fontSize:40,color:C.muted,lineHeight:1.6}}>{sub}</div></div>)}</div>
 </div><Small>其他扩展按资料分别启用与连接；不是内嵌浏览器。</Small></AbsoluteFill>
}

function Outro(){
 const f=useCurrentFrame();const crane=v(f,[0,40],[0,1],Easing.bezier(.3,0,.2,1));const recede=v(f,[42,50],[0,1]);
 const sweepX=v(f,[2,14],[-700,2020],Easing.bezier(.4,0,.6,1)),sweepOpacity=v(f,[2,5,11,14],[0,.12,.12,0]);
 const stageLight=v(f,[42,50,58],[0,.5,.25]),vignette=v(f,[42,54],[0,.1]);
 const ruleExt=v(f,[58,66],[0,1],Easing.bezier(.3,0,.2,1)),ruleExtFade=v(f,[66,72],[1,0]);
 const els=[
  {file:'popup-all.png',x:255,y:420,w:320,h:390,scale:1.0,rot:-4,dx:-450,dy:-160,cue:4},
  {file:'shop-1.png',x:1555,y:325,w:420,h:208,scale:.95,rot:4,dx:450,dy:-180,cue:7},
  {file:'search.png',x:955,y:205,w:296,h:31,scale:1.75,rot:-1.5,dx:0,dy:-300,cue:10},
  {file:'profile-panel.png',x:1640,y:755,w:284,h:462,scale:.78,rot:-3,dx:420,dy:260,cue:13},
  {file:'shop-3.png',x:330,y:850,w:420,h:208,scale:.95,rot:3,dx:-400,dy:250,cue:16}
 ];
 return <AbsoluteFill style={{background:C.bg}}>
  <div style={{position:'absolute',inset:0,transform:`perspective(1400px) rotateX(${4*(1-crane)}deg) scale(${1.06-.06*crane})`,transformOrigin:'50% 45%'}}>
   <AbsoluteFill style={{background:'radial-gradient(ellipse at 50% 44%,#ffffff,#e8f0ec 80%)'}}/>
   {els.map(el=>{const t=v(f,[el.cue,el.cue+12],[0,1],fly);const a=v(f,[el.cue,el.cue+3],[0,1])*(1-.12*recede);const lin=v(f,[el.cue,el.cue+12],[0,1]);const air=Math.max(0,1-t);return <React.Fragment key={el.file}>
    {lin>.05&&lin<.95&&<div style={{position:'absolute',left:el.x-el.w/2,top:el.y-el.h/2,width:el.w,height:el.h,transform:`translate(${el.dx*(1-t)+el.dx*.08}px,${el.dy*(1-t)+el.dy*.08}px) rotate(${el.rot*(2-t)}deg) scale(${el.scale*(1.12-.12*t)})`,opacity:.2*(1-lin),filter:'blur(8px)',overflow:'hidden',borderRadius:15}}><Img src={tex(el.file)} style={{width:'100%',height:'100%'}}/></div>}
    <div style={{position:'absolute',left:el.x-el.w/2,top:el.y-el.h/2,width:el.w,height:el.h,transform:`translate(${el.dx*(1-t)}px,${el.dy*(1-t)}px) rotate(${el.rot*(2-t)}deg) scale(${el.scale*(1.12-.12*t)})`,opacity:a,filter:`saturate(${1-.08*recede}) blur(${recede*1.2}px)`,overflow:'hidden',borderRadius:15,boxShadow:`0 ${10+26*air}px ${24+46*air}px rgba(22,61,52,${.16+.1*air}),0 2px 6px #163d3414`,border:'1px solid #dfe6e2'}}><Img src={tex(el.file)} style={{width:'100%',height:'100%'}}/></div>
   </React.Fragment>})}
  </div>
  <AbsoluteFill style={{background:'radial-gradient(ellipse 740px 420px at 50% 48%,#f5f7f6 70%,#f5f7f600)',opacity:recede}}/>
  {sweepOpacity>0&&<div style={{position:'absolute',top:0,bottom:0,left:sweepX-300,width:600,background:'linear-gradient(90deg,#c3e2d400,#c3e2d4 50%,#c3e2d400)',opacity:sweepOpacity,mixBlendMode:'multiply'}}/>}
  {stageLight>0&&<AbsoluteFill style={{background:'radial-gradient(700px 360px at 960px 470px,rgba(195,226,212,.95),rgba(195,226,212,.35) 55%,rgba(195,226,212,0) 75%)',opacity:stageLight}}/>}
  {vignette>0&&<AbsoluteFill style={{background:'radial-gradient(1400px 900px at 50% 50%,rgba(22,61,52,0) 55%,rgba(22,61,52,.7) 100%)',opacity:vignette}}/>}
  {Array.from({length:20},(_,i)=><div key={i} style={{position:'absolute',left:(i*439+137)%1920+Math.sin(Math.min(f,120)*.025+i)*12,top:((i*613+271)%1080)-Math.min(f,120)*(.3+(i%5)*.11),width:2+i%3*.5,height:2+i%3*.5,borderRadius:5,background:'#235c50',opacity:(.15+(i%4)*.05)*v(f,[0,30],[0,1])}}/>)}
  <div style={{position:'absolute',top:90,left:0,right:0,textAlign:'center',fontSize:36,color:C.green,letterSpacing:3,opacity:v(f,[30,45],[0,1])}}>CHROME 商店已上线 · MIT 开源</div>
  <div style={{position:'absolute',top:345,left:490,width:940,textAlign:'center'}}>
   <div style={{fontSize:144,fontWeight:650,letterSpacing:-5,display:'flex',justifyContent:'center'}}>{'快店快点'.split('').map((c,i)=>{const t=v(f,[42+i*1.8,50+i*1.8],[0,1],Easing.bezier(.2,.75,.3,1));return <span key={i} style={{opacity:t,transform:`translateY(${(1-t)*28}px) scale(${1.35-.35*t})`,filter:`blur(${(1-t)*8}px)`}}>{c}</span>})}</div>
   <div style={{position:'relative',height:6,width:260,margin:'34px auto 0'}}><div style={{position:'absolute',inset:0,borderRadius:3,background:C.green,transform:`scaleX(${v(f,[58,70],[0,1],Easing.bezier(.3,0,.2,1))})`}}/>
    {ruleExt>0&&ruleExtFade>0&&<><div style={{position:'absolute',top:2.5,height:1,right:'100%',width:190*ruleExt,background:C.green,opacity:ruleExtFade}}/><div style={{position:'absolute',top:2.5,height:1,left:'100%',width:190*ruleExt,background:C.green,opacity:ruleExtFade}}/></>}
   </div>
   <div style={{fontSize:44,background:C.green,color:'#fff',padding:'22px 18px',borderRadius:18,marginTop:45,opacity:v(f,[68,80],[0,1])}}>Chrome 商店搜索「快店快点」</div>
   <div style={{fontSize:38,color:C.muted,marginTop:30,opacity:v(f,[80,92],[0,1])}}>安装扩展 + 配套本地助手</div>
  </div>
  <div style={{position:'absolute',left:0,right:0,bottom:48,textAlign:'center',fontSize:36,color:C.green,opacity:v(f,[92,104],[0,1])}}>cartmancxx.github.io/kuaidian-kuaidian</div>
 </AbsoluteFill>;
}

export const SFX=[
 {from:SHOTS.hero.from+45,src:'whoosh.wav',vol:.33,dur:35,note:'hero lift'},
 {from:SHOTS.hero.from+60,src:'sparkle.wav',vol:.16,dur:40,note:'single hero perimeter beam'},
 {from:SHOTS.hero.from+130,src:'tap.wav',vol:.32,dur:12,note:'hero lands flush'},
 {from:SHOTS.search.from,src:'whoosh.wav',vol:.22,dur:35,note:'search scene entry'},
 {from:SHOTS.search.from+45,src:'tap.wav',vol:.22,dur:8,note:'input first glyph'},
 {from:SHOTS.search.from+60,src:'tap.wav',vol:.19,dur:8,note:'input second glyph'},
 {from:SHOTS.search.from+90,src:'tap.wav',vol:.16,dur:8,note:'complete store search'},
 {from:SHOTS.search.from+130,src:'tap.wav',vol:.45,dur:12,note:'click store entry'},
 {from:SHOTS.bind.from+32,src:'whoosh.wav',vol:.26,dur:35,note:'camera pushes toward binding'},
 {from:SHOTS.map.from,src:'impact.wav',vol:.3,dur:50,note:'profile planning scene'},
 {from:SHOTS.native.from,src:'whoosh.wav',vol:.25,dur:35,note:'native browser breath card'},
 {from:SHOTS.outro.from,src:'riser.wav',vol:.3,dur:42,note:'launch photo assembly'},
 {from:SHOTS.outro.from+42,src:'impact.wav',vol:.48,dur:60,note:'brand arrives'},
 {from:SHOTS.outro.from+67,src:'sparkle.wav',vol:.22,dur:50,note:'brand underline afterglow'}
];

export const Film:React.FC<{bgm:boolean}>=({bgm})=>{
 const frame=useCurrentFrame();
 return <AbsoluteFill style={{fontFamily:FONT,color:C.ink,background:C.bg}}>
  <Sequence from={SHOTS.hero.from} durationInFrames={SHOTS.hero.duration}><Hero/></Sequence><Sequence from={SHOTS.search.from} durationInFrames={SHOTS.search.duration}><Search/></Sequence><Sequence from={SHOTS.bind.from} durationInFrames={SHOTS.bind.duration}><Bind/></Sequence><Sequence from={SHOTS.map.from} durationInFrames={SHOTS.map.duration}><ProfileMap/></Sequence><Sequence from={SHOTS.native.from} durationInFrames={SHOTS.native.duration}><Native/></Sequence><Sequence from={SHOTS.outro.from} durationInFrames={SHOTS.outro.duration}><Outro/></Sequence>
  {bgm&&<Audio src={staticFile('audio/bgm.wav')} volume={(f)=>.46*v(f,[0,15,915,960],[0,1,1,0])}/>}
  {SFX.map((s,i)=><Sequence key={i} from={s.from} durationInFrames={s.dur}><Audio src={staticFile('audio/'+s.src)} volume={s.vol}/></Sequence>)}
  <div style={{position:'absolute',left:0,right:0,bottom:0,height:4,background:'#235c5014'}}><div style={{height:'100%',width:`${frame/959*100}%`,background:C.green}}/></div>
 </AbsoluteFill>;
};
