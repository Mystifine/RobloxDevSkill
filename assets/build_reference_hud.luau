-- Studio authoring command only. Creates static instances; no runtime code is installed.
local SG = game:GetService('StarterGui')
local C = Color3.fromRGB
local ink = C(28,24,35)
local function make(class, name, parent, props)
 local o=Instance.new(class) o.Name=name
 for k,v in props or {} do o[k]=v end o.Parent=parent return o
end
local function box(name,parent,x,y,w,h)
 return make('Frame',name,parent,{BackgroundTransparency=1,BorderSizePixel=0,AnchorPoint=Vector2.new(.5,.5),Position=UDim2.fromScale(x,y),Size=UDim2.fromScale(w,h)})
end
local function round(o,r) make('UICorner','RoundedCorners',o,{CornerRadius=UDim.new(r,0)}) end
local function stroke(o,color,width,mode)
 return make('UIStroke','Outline',o,{Color=color or ink,Thickness=width or 2,ApplyStrokeMode=mode or Enum.ApplyStrokeMode.Border,BorderStrokePosition=Enum.BorderStrokePosition.Inner,LineJoinMode=Enum.LineJoinMode.Round})
end
local function text(parent,name,value,x,y,w,h,color)
 local o=make('TextLabel',name,parent,{AnchorPoint=Vector2.new(.5,.5),Position=UDim2.fromScale(x,y),Size=UDim2.fromScale(w,h),BackgroundTransparency=1,Text=value,TextColor3=color or C(255,255,255),Font=Enum.Font.GothamBlack,TextScaled=true,TextWrapped=false,ZIndex=10})
 make('UITextSizeConstraint','ReadableText',o,{MinTextSize=8,MaxTextSize=40})
 stroke(o,ink,2,Enum.ApplyStrokeMode.Contextual) return o
end
local function plate(parent,name,x,y,w,h,top,bottom,cols,rows)
 local p=make('ImageButton',name,parent,{AnchorPoint=Vector2.new(.5,.5),Position=UDim2.fromScale(x,y),Size=UDim2.fromScale(w,h),Image='',BackgroundColor3=top,BorderSizePixel=0,AutoButtonColor=false})
 round(p,.13) stroke(p,ink,3)
 make('UIGradient','ColorWash',p,{Color=ColorSequence.new(top,bottom),Rotation=90})
 local face=box('InsetFace',p,.5,.5,.945,.91) face.BackgroundTransparency=1 round(face,.11)
 local pattern=box('StudPattern',p,.5,.5,.91,.83) pattern.ClipsDescendants=true
 for row=1,rows do for col=1,cols do
  local stud=box('Stud',pattern,(col-.5)/cols,(row-.5)/rows,.69/cols,.64/rows)
  stud.BackgroundColor3=C(255,255,255) stud.BackgroundTransparency=.83 round(stud,.16)
  local s=stroke(stud,C(104,66,26),1) s.Transparency=.75
 end end
 local shine=box('Gloss',p,.5,.24,.76,.26) shine.AnchorPoint=Vector2.new(.5,0) shine.Position=UDim2.new(.5,0,0,6) shine.BackgroundColor3=C(255,255,255) shine.BackgroundTransparency=.68 round(shine,.3)
 make('UIGradient','Fade',shine,{Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,.1),NumberSequenceKeypoint.new(1,1)}),Rotation=90})
 local sheen=box('DiagonalShine',p,.5,.5,.86,.78) sheen.ClipsDescendants=true
 for i=1,3 do local b=box('LightBand',sheen,.10+i*.26,.5,.075,1.7) b.BackgroundColor3=C(255,255,255) b.BackgroundTransparency=.72 b.Rotation=-25 b:SetAttribute('AllowBleed',true) b:SetAttribute('BleedReason','Diagonal gloss intentionally cropped to plate interior') end
 if name=='AddFriend' then pattern:Destroy() shine:Destroy() sheen:Destroy() end
 return p
end
local atlas='rbxassetid://136387010934188'
local rects={{3,83,334,345},{344,111,270,297},{624,126,349,270},{971,105,277,322},{6,474,315,329},{331,480,303,322},{657,473,290,323},{945,489,306,308},{5,823,356,365},{352,864,299,313},{650,833,286,362},{933,875,317,312}}
local function icon(parent,name,index,x,y,w,h)
 local o=make('ImageLabel',name,parent,{AnchorPoint=Vector2.new(.5,.5),Position=UDim2.fromScale(x,y),Size=UDim2.fromScale(w,h),BackgroundTransparency=1,Image=atlas,ScaleType=Enum.ScaleType.Fit,ZIndex=5})
 -- Roblox transcodes this 1254px source atlas to a 1024px texture.
 local r=rects[index] local k=1024/1254 o.ImageRectOffset=Vector2.new(math.round(r[1]*k),math.round(r[2]*k)) o.ImageRectSize=Vector2.new(math.round(r[3]*k),math.round(r[4]*k))
 o:SetAttribute('AtlasIndex',index) return o
end
local function currency(parent,name,value,x,y,w,h,prefix)
 local g=box(name,parent,x,y,w,h)
 -- Roblox's native Robux character keeps the icon and amount on one baseline.
 local label=text(g,'Price',(prefix or '')..utf8.char(0xE002)..' '..value,.5,.5,1,.95,C(133,255,129))
 label.Outline.Thickness=1.5
 return g
end
local function badge(parent)
 -- Reference notification intentionally overlaps the card's top right corner.
 local b=box('Notification',parent,.94,.045,.27,.27) b.BackgroundTransparency=0 b.BackgroundColor3=C(255,44,36) make('UIAspectRatioConstraint','Square',b,{AspectRatio=1}) round(b,.5) stroke(b,C(129,19,18),2) b.ZIndex=20 b:SetAttribute('AllowBleed',true) b:SetAttribute('BleedReason','Notification overlaps its own card corner as in reference')
 text(b,'Exclamation','!',.5,.43,.64,.8).ZIndex=21
end
local function constrain(o,ratio,minX,minY,maxX,maxY)
 make('UIAspectRatioConstraint','Proportions',o,{AspectRatio=ratio,DominantAxis=Enum.DominantAxis.Width})
 make('UISizeConstraint','DeviceSizeLimits',o,{MinSize=Vector2.new(minX,minY),MaxSize=Vector2.new(maxX,maxY)})
end
for _,n in {'ReferenceSimulatorHUD','ReferenceSimulatorTopbar'} do if SG:FindFirstChild(n) then SG[n]:Destroy() end end
local gui=make('ScreenGui','ReferenceSimulatorHUD',SG,{ResetOnSpawn=false,DisplayOrder=10,ZIndexBehavior=Enum.ZIndexBehavior.Sibling,ScreenInsets=Enum.ScreenInsets.CoreUISafeInsets,SafeAreaCompatibility=Enum.SafeAreaCompatibility.None,ClipToDeviceSafeArea=true})
gui:SetAttribute('VisualOnly',true) gui:SetAttribute('Reference','User supplied simulator HUD screenshot')
local root=box('HUD',gui,.5,.5,1,1)

local nav=box('Navigation',root,.01,.47,.125,.38) nav.AnchorPoint=Vector2.new(0,.5) constrain(nav,.69,108,157,240,348)
local grid=make('UIGridLayout','TwoColumnGrid',nav,{CellSize=UDim2.fromScale(.46,.303),CellPadding=UDim2.fromScale(.075,.043),SortOrder=Enum.SortOrder.LayoutOrder})
local entries={{'Shop','SHOP',1,C(255,250,156),C(255,169,38)},{'Rebirth','REBIRTH',2,C(235,255,255),C(52,186,255)},{'Pets','PETS',3,C(255,220,240),C(255,57,133)},{'Trails','TRAILS',4,C(239,227,255),C(153,87,255)},{'Inventory','INVENTORY',5,C(255,247,171),C(255,157,39)},{'FreeGifts','FREE GIFTS',6,C(255,246,176),C(255,171,38)}}
for i,e in entries do
 local p=plate(nav,e[1],.5,.5,.46,.303,e[4],e[5],7,7) p.LayoutOrder=i
 icon(p,'Illustration',e[3],.5,.42,.77,.60)
 text(p,'Caption',e[2],.5,.82,.97,.23)
 if i==2 then local t=text(p,'RebirthReady','100%',.5,.025,.80,.25,C(157,255,143)) t:SetAttribute('AllowBleed',true) t:SetAttribute('BleedReason','Readiness label straddles top edge in reference') end
 if i==2 or i==5 or i==6 then badge(p) end
 task.wait()
end
local auto=plate(root,'AutoShoot',.5,.012,.14,.045,C(255,224,225),C(255,62,82),17,3) auto.AnchorPoint=Vector2.new(.5,0) constrain(auto,6.35,142,25,270,43)
text(auto,'Caption','AUTO SHOOT',.5,.48,.88,.61)
local ap=currency(auto,'RobuxPrice','25',.5,1.02,.23,.47) ap:SetAttribute('AllowBleed',true) ap:SetAttribute('BleedReason','Price hangs beneath the Auto Shoot plate in reference')

local offers=box('Offers',root,.989,.28,.092,.35) offers.AnchorPoint=Vector2.new(1,.5) constrain(offers,.55,89,162,177,322)
local starter=make('ImageButton','StarterPack',offers,{BackgroundTransparency=1,Image='',Position=UDim2.fromScale(.5,.22),AnchorPoint=Vector2.new(.5,.5),Size=UDim2.fromScale(1,.43),AutoButtonColor=false})
icon(starter,'GiftBundle',9,.5,.43,.94,.84) text(starter,'Caption','STARTER PACK',.5,.91,1,.18,C(255,228,147))
local str=plate(offers,'DoubleStrength',.5,.58,1,.21,C(222,255,151),C(91,206,49),13,4)
icon(str,'StrengthWatermark',7,.5,.47,.65,.65).ImageTransparency=.60
text(str,'Caption','2X STRENGTH',.5,.43,.91,.35)
local price=currency(str,'Price','3',.5,.96,.95,.35,'ONLY ') price:SetAttribute('AllowBleed',true) price:SetAttribute('BleedReason','Offer price hangs over its own lower border')
local wins=plate(offers,'DoubleWins',.5,.845,1,.21,C(255,242,170),C(255,181,54),13,4)
icon(wins,'TrophyWatermark',8,.5,.5,.7,.65).ImageTransparency=.60
text(wins,'Caption','2X WINS',.5,.43,.91,.35)
local wp=currency(wins,'Price','59',.5,.96,.95,.35,'ONLY ') wp:SetAttribute('AllowBleed',true) wp:SetAttribute('BleedReason','Offer price hangs over its own lower border')

local bottom=box('Progression',root,.5,.986,.365,.24) bottom.AnchorPoint=Vector2.new(.5,1) constrain(bottom,3.03,330,109,700,231)
local header=box('StrengthHeader',bottom,.5,.095,1,.18)
icon(header,'Biceps',7,.04,.5,.07,1)
text(header,'StrengthValue','413.9k',.145,.5,.14,.94,C(255,177,72))
text(header,'StrengthCaption','STRENGTH',.30,.55,.16,.56)
text(header,'Multiplier','x5 Multiplier',.90,.5,.20,.72,C(185,228,255))
local level=plate(bottom,'LevelBar',.5,.36,1,.31,C(255,244,87),C(255,175,17),48,5)
text(level,'Level','Level 100',.18,.5,.30,.50,C(255,255,237))
text(level,'Progress','16.1k/16.1k',.82,.5,.30,.50,C(255,255,237))
local boosts=box('StrengthBoosts',bottom,.5,.79,1,.38)
make('UIGridLayout','BoostRow',boosts,{CellSize=UDim2.fromScale(.318,.82),CellPadding=UDim2.fromScale(.023,.0),SortOrder=Enum.SortOrder.LayoutOrder})
for i,e in {{'+10K','11',C(255,244,153),C(255,190,32)},{'+100K','45',C(255,200,200),C(255,72,84)},{'+1M','95',C(223,246,255),C(172,88,244)}} do
 local p=plate(boosts,'Boost'..i,.5,.5,.318,.82,e[3],e[4],15,5) p.LayoutOrder=i
 icon(p,'Biceps',7,.18,.50,.25,.64)
 text(p,'Amount',e[1],.62,.45,.60,.48,i==3 and C(182,232,255) or C(255,250,239))
 local cp=currency(p,'Price',e[2],.77,1.01,.37,.43) cp:SetAttribute('AllowBleed',true) cp:SetAttribute('BleedReason','Robux price hangs beneath its boost card in reference')
end

-- A constrained transparent dock lifts the stats above progression on narrow portrait screens.
local statsDock=box('StatsDock',root,0,.69,1,.30) statsDock.AnchorPoint=Vector2.new(0,0)
make('UIAspectRatioConstraint','ResponsiveDock',statsDock,{AspectRatio=4.7,AspectType=Enum.AspectType.FitWithinMaxSize,DominantAxis=Enum.DominantAxis.Width})
local stats=box('PlayerStats',statsDock,.008,1,.20,1) stats.AnchorPoint=Vector2.new(0,1) constrain(stats,1.83,156,85,280,153)
stats:SetAttribute('AllowBleed',true) stats:SetAttribute('BleedReason','Stats may extend above their transparent positioning dock; visible content stays inside the screen')
for i,e in {{'RebirthRow','RebirthIcon',2,'Rebirths','4',C(115,204,255)},{'WinsRow','WinsIcon',8,'Wins','2.4k',C(255,217,113)}} do
 local row=box(e[1],stats,.5,i==1 and .17 or .51,1,.30)
 make('UIListLayout','IconAmountRow',row,{FillDirection=Enum.FillDirection.Horizontal,VerticalAlignment=Enum.VerticalAlignment.Center,Padding=UDim.new(0,6),SortOrder=Enum.SortOrder.LayoutOrder})
 local image=icon(row,e[2],e[3],.5,.5,1,1) image.Size=UDim2.fromScale(1,1) image.LayoutOrder=1
 make('UIAspectRatioConstraint','Square',image,{AspectRatio=1,DominantAxis=Enum.DominantAxis.Height})
 local amount=text(row,e[4],e[5],.5,.5,.70,.86,e[6]) amount.TextXAlignment=Enum.TextXAlignment.Left amount.LayoutOrder=2
end
local friend=box('FriendRow',stats,.5,.85,1,.24) friend.Size=UDim2.new(1,0,.24,4)
make('UIListLayout','FriendRowLayout',friend,{FillDirection=Enum.FillDirection.Horizontal,VerticalAlignment=Enum.VerticalAlignment.Center,Padding=UDim.new(0,6),SortOrder=Enum.SortOrder.LayoutOrder})
local friendText=text(friend,'FriendBoost','Friend Boost: +0%',.5,.5,1,.84) friendText.Size=UDim2.new(1,-36,.84,0) friendText.TextXAlignment=Enum.TextXAlignment.Left friendText.LayoutOrder=1
local plus=plate(friend,'AddFriend',.5,.5,1,1,C(160,255,152),C(49,177,62),2,2) plus.Size=UDim2.fromScale(1,1) plus.LayoutOrder=2 plus.Outline.Thickness=2
make('UIAspectRatioConstraint','Square',plus,{AspectRatio=1,DominantAxis=Enum.DominantAxis.Height})
make('UISizeConstraint','PlateSize',plus,{MinSize=Vector2.new(24,24),MaxSize=Vector2.new(28,28)})
text(plus,'Plus','+',.5,.5,.68,.68).Outline.Thickness=1

local top=make('ScreenGui','ReferenceSimulatorTopbar',SG,{ResetOnSpawn=false,DisplayOrder=11,ZIndexBehavior=Enum.ZIndexBehavior.Sibling,ScreenInsets=Enum.ScreenInsets.TopbarSafeInsets,SafeAreaCompatibility=Enum.SafeAreaCompatibility.None}) top:SetAttribute('VisualOnly',true)
-- Measured in Play: native plates are 44px tall and end 2px above this inset's bottom.
-- Bottom anchoring follows the engine's inset height without a runtime alignment script.
local toolsFrame=make('Frame','QuickAccess',top,{BackgroundTransparency=1,Size=UDim2.new(1,-4,0,44),AnchorPoint=Vector2.new(0,1),Position=UDim2.new(0,4,1,-2)})
make('UISizeConstraint','ToolbarWidth',toolsFrame,{MinSize=Vector2.new(176,44),MaxSize=Vector2.new(206,44)})
-- Distribute remaining width across three gaps; round the offset down to prevent edge overflow.
make('UIListLayout','ToolbarRow',toolsFrame,{FillDirection=Enum.FillDirection.Horizontal,Padding=UDim.new(1/3,-59),VerticalAlignment=Enum.VerticalAlignment.Center,SortOrder=Enum.SortOrder.LayoutOrder})
for i,e in {{'Settings',0},{'DailyRewards',10},{'Quests',11},{'Index',12}} do
 local b=make('ImageButton',e[1],toolsFrame,{Image='',BackgroundColor3=C(22,37,43),BackgroundTransparency=.06,Size=UDim2.fromOffset(44,44),AutoButtonColor=false,LayoutOrder=i}) round(b,.5)
 if e[2]==0 then text(b,'Gear','⚙',.5,.49,.72,.75,C(237,246,255)).Font=Enum.Font.GothamBold else icon(b,'Illustration',e[2],.5,.5,.72,.72) end
 if i==2 then badge(b) b.Notification.Position=UDim2.fromScale(.91,.15) end
end
game:GetService('Selection'):Set({gui})
return {hud=gui:GetFullName(),topbar=top:GetFullName(),descendants=#gui:GetDescendants()+#top:GetDescendants(),scripts=0}
