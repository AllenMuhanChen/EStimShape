function makeNatGrat

global Gtxtr Mstate screenPTR loopTrial screenNum

Screen('Close')  %First clean up: Get rid of all textures/offscreen windows
Gtxtr = [];   %reset

%get parameters set in GUI
Pstruct = getParamStruct;

%get screen settings
screenRes = Screen('Resolution',screenNum);


%stimulus parameters
ori=[0:30:150];
sf=[0.05 0.1 0.15 0.2];
phase=[0 90 180 270];

textureBase='/nat scenes/512 px/B';
textureCond={'base';'ps';'synth'};
NtextureBase=40;
NtextureCond=[1 2 2];

natsceneBase='/nat scenes/512 px/VH';
natsceneCond={'base';'ps';'thresh'};
natsceneThres={'0.25';'0.50';'0.75'};
NnatsceneBase=20;
NnatsceneCond=[1 2 3];



%get nrs of stim per condition and construct condition vector
Ngrating=length(ori)*length(sf)*length(phase);
[oridom,sfdom,phasedom]=ndgrid(ori,sf,phase);
oridom=oridom(:);
sfdom=sfdom(:);
phasedom=phasedom(:);

Ntexture=sum(NtextureBase*NtextureCond);
c=1;
for i=1:length(textureCond)
   for j=1:NtextureCond(i)
       for k=1:NtextureBase
           textureBaseDom{c}=textureCond{i};
           textureIdxDom(c)=k;
           textureCondDom(c)=j;
           
           c=c+1;
       end
   end
end

Nnatscene=sum(NnatsceneBase*NnatsceneCond);
c=1;
for i=1:length(natsceneCond)
   for j=1:NnatsceneCond(i)
       for k=1:NnatsceneBase
           natsceneBaseDom{c}=natsceneCond{i};
           natsceneIdxDom(c)=k;
           natsceneCondDom(c)=j;
           
           c=c+1;
       end
   end
end


%this calculation is based on the assumption that the screen is round
pxDeg = 2*pi/360*Mstate.screenDist*screenRes.width/Mstate.screenXcm;  % pixels per degree
x_deg=Pstruct.x_px/pxDeg;
y_deg=Pstruct.y_px/pxDeg;


%make grating
if Pstruct.cond<=Ngrating        

    condTrial{1} ='grating';
    condTrial{2} = oridom(Pstruct.cond);
    condTrial{3} = sfdom(Pstruct.cond);
    condTrial{4} = phasedom(Pstruct.cond);
    condTrial{5} = Pstruct.contrast;
    
    x_ecc = x_deg/2;
    y_ecc = y_deg/2;
        
    x_ecc = single(linspace(-x_ecc,x_ecc,Pstruct.x_px));  %deg
    y_ecc = single(linspace(-y_ecc,y_ecc,Pstruct.y_px));
    
    [x_ecc y_ecc] = meshgrid(x_ecc,y_ecc);
   
    sdom = x_ecc*cos(oridom(Pstruct.cond)*pi/180) - y_ecc*sin(oridom(Pstruct.cond)*pi/180);    %deg
    sdom = sdom*sfdom(Pstruct.cond)*2*pi + pi; %radians
    temp = cos(sdom - phasedom(Pstruct.cond)*pi/180);
    temp = temp*Pstruct.contrast/100;
    
    temp=(temp+1)/2;
    temp=uint8(round(temp*255));
    
    Gtxtr = Screen(screenPTR, 'MakeTexture', temp);

elseif Pstruct.cond>Ngrating & Pstruct.cond<=Ngrating+Ntexture
    
    c=Pstruct.cond-Ngrating;
    
    condTrial{1}='texture';
    condTrial{2} = textureBaseDom(c);
    condTrial{3} = textureIdxDom(c);
    condTrial{4} = textureCondDom(c);
    condTrial{5} = Pstruct.contrast;
    
    %generate file name
    if strcmp(textureBaseDom(c),'base')
        textName=[textureBase num2str(textureIdxDom(c)) '-' textureBaseDom{c} '.png'];
    else
        textName=[textureBase num2str(textureIdxDom(c)) '-' ...
            textureBaseDom{c} num2str(textureCondDom(c)) '.png'];
    end   
    
    img=imread(textName);
    
    Gtxtr = Screen(screenPTR, 'MakeTexture', img);

else
    
    c=Pstruct.cond-Ngrating-Ntexture;
    
    condTrial{1}='nat scene';
    condTrial{2} = natsceneBaseDom(c);
    condTrial{3} = natsceneIdxDom(c);
    condTrial{4} = natsceneCondDom(c);
    condTrial{5} = Pstruct.contrast;

    %generate file name
    if strcmp(natsceneBaseDom(c),'base')
        natName=[natsceneBase num2str(natsceneIdxDom(c)) '-' natsceneBaseDom{c} '.png'];
    elseif strcmp(natsceneBaseDom(c),'ps')
        natName=[natsceneBase num2str(natsceneIdxDom(c)) '-' ...
            natsceneBaseDom{c} num2str(natsceneCondDom(c)) '.png'];
    else
        natName=[natsceneBase num2str(natsceneIdxDom(c)) '-' ...
           natsceneBaseDom{c} natsceneThres{natsceneCondDom(c)} '.png'];
    end   
    
    
    img=imread(natName);
    
    Gtxtr = Screen(screenPTR, 'MakeTexture', img);
    
end

if Mstate.running
    
    saveLog_NatGrat(loopTrial,condTrial);

end
