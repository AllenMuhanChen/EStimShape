%%we're using the brodartz texture database
function makeBTexture


global Gtxtr Mstate screenPTR  screenNum

Screen('Close')  %First clean up: Get rid of all textures/offscreen windows
Gtxtr = [];   %reset

%get screen settings
screenRes = Screen('Resolution',screenNum);



%get parameters set in GUI
Pstruct = getParamStruct;


%this calculation is based on the assumption that the screen is round
pxDeg = 2*pi/360*Mstate.screenDist*screenRes.width/Mstate.screenXcm;  % pixels per degree

%stimulus size
stimSize=[Pstruct.x_size Pstruct.y_size];
stimSizePx=round(stimSize*pxDeg);



%stimulus parameters
textureBase='/brodatz/';

textureName={'bark';'brick';'bubbles';'grass';'leather';'pigskin';...
    'raffia';'sand';'straw';'water';'weave';'wood';'wool'};
Ntexture=length(textureName);


tempName=[textureBase textureName{Pstruct.textureId} '.' sprintf('%03d',Pstruct.angle) '.tiff'];
tempImg=imread(tempName);
    
imgOldSize=size(tempImg);
imgHalf=round(imgOldSize/2);
imgNewSize=imgHalf/Pstruct.zoom;

img=tempImg(imgHalf-imgNewSize+1:imgHalf+imgNewSize,imgHalf-imgNewSize+1:imgHalf+imgNewSize);
img=imresize(img,stimSizePx);


Gtxtr = Screen(screenPTR, 'MakeTexture', img);
    



        
        