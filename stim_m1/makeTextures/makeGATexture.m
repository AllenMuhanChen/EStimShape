%%we're using the brodartz texture database
function makeGATexture

global Gtxtr Mstate screenPTROff2 screenNum screenPTR

Screen('Close')  %First clean up: Get rid of all textures/offscreen windows

Gtxtr = [];   %reset
screenPTROff2=Screen('OpenOffscreenWindow',screenPTR,[],[],[],[],8);
Screen(screenPTROff2,'BlendFunction',GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);


%get screen size
screenRes = Screen('Resolution',screenNum);

%get parameters set in GUI
Pstruct = getParamStruct;

%this calculation is based on the assumption that the screen is round
pxDeg = 2*pi/360*Mstate.screenDist*screenRes.width/Mstate.screenXcm;  % pixels per degree

%read image?
folderName = [Mstate.anim '_r-' num2str(Pstruct.GArun)];
%load([Pstruct.stimpath folderName '_currExptInfo.mat']);

c=Pstruct.contrast/100;
fore_col = round(255*[Pstruct.fore_r Pstruct.fore_g Pstruct.fore_b]);
if c==0
    fore_col=Pstruct.background;
end

if Pstruct.useBubbles == 0
    fullFolderName = [folderName '_g-' num2str(Pstruct.genNum)];
    load([Pstruct.stimpath fullFolderName '/stimParams.mat']);
    
    stim = stimuli{Pstruct.linNum,Pstruct.stimnr}; %#ok<USENS>
    cPts = [stim.cPts(:,1) -stim.cPts(:,2)];   
    cPts = movePts(cPts,stim.xPos,stim.yPos,stim.siz*pxDeg,stim.ori); 
    
    concatenatedSplines = drawSpline(cPts,200);
else
    fullFolderName = [folderName '_p'];
    load([Pstruct.stimpath fullFolderName '/maskParams.mat']);
    
    if Pstruct.stimnr>length(stimuli{Pstruct.linNum})
        disp('incorrect stimulus number selected!!!!!')
    end
    
    stim = stimuli{Pstruct.linNum}{Pstruct.stimnr};
    
    cPts = [stim.cPts(:,1) -stim.cPts(:,2)];
    cPts = movePts(cPts,stim.xPos,stim.yPos,stim.siz*pxDeg,stim.ori); 
    concatenatedSplines = drawSpline(cPts,200);
    
    maskwidth=screenRes.width;
    maskheight=screenRes.height;
    
    [wmat,hmat]=meshgrid(1:maskwidth,1:maskheight);
    
    mask=ones(maskheight,maskwidth,4);
    
    for i=1:3
        mask(:,:,i)=round(mask(:,:,i)*Pstruct.maskcolor);
    end
    
    masktmp=zeros(maskheight,maskwidth);
    
    for maskNum=1:3
        temp = zeros(maskheight,maskwidth);
        center = round(movePts([stim.mask{maskNum}.x -stim.mask{maskNum}.y],stim.xPos,stim.yPos,stim.siz*pxDeg,stim.ori));
        siz = stim.mask{maskNum}.s*stim.siz*pxDeg;
%         masktmp = gauss2d(masktmp,siz,center);
        [~,rad]=cart2pol(wmat-center(1),hmat-center(2));
        
%         innerRad = 0.8;
%         slopeInd = 1:-0.005:innerRad;
%         alphaVals = linspace(0,1,length(slopeInd));
%         for i=1:length(slopeInd)
%             temp(rad<slopeInd(i)*siz) = alphaVals(i);
%         end
        
        temp(rad<siz) = 1;

        masktmp = temp + masktmp;
%         masktmp(rad>siz) = 0;
    end
    masktmp(masktmp>1) = 1;
    
    kernel = makeKernel([1 1],[10 10],[4 4]);
    masktmp = padarray(masktmp,[40 40]);
    masktmp = conv2(masktmp,kernel,'valid');
    
    save('/Users/nielsenlab/Desktop/temp.mat','masktmp');
%     h = fspecial('average',[10 10]);
%     masktmp=filter2(h, masktmp);

    maskWindowCenter = round(min(concatenatedSplines) + (max(concatenatedSplines) - min(concatenatedSplines)) / 2);
    maskWindowSize = round(max(max(concatenatedSplines) - min(concatenatedSplines)));
    
    maskWindowXLims = [1:(maskWindowCenter(1) - maskWindowSize), (maskWindowCenter(1) + maskWindowSize):maskwidth];
    maskWindowYLims = [1:(maskWindowCenter(2) - maskWindowSize), (maskWindowCenter(2) + maskWindowSize):maskheight];
    
    maskWindowXLims(maskWindowXLims > maskwidth) = maskwidth;
    maskWindowYLims(maskWindowYLims > maskheight) = maskheight;
    maskWindowXLims(maskWindowXLims < 1) = 1;
    maskWindowYLims(maskWindowYLims < 1) = 1;
    
    masktmp(maskWindowYLims,:) = 1;
    masktmp(:,maskWindowXLims) = 1;

    %save('/Users/nielsenlab/Desktop/temp.mat','masktmp','maskWindowXLims','maskWindowYLims');
    
    
    masktmp=1-masktmp; %everything that is 1 in the mask will be set to the mask color
    save('/Users/nielsenlab/Desktop/temp2.mat','masktmp');
    
    mask(:,:,4)=mask(:,:,4)+masktmp*255;
end


Screen(screenPTROff2, 'FillRect', Pstruct.background);
Screen('FillPoly',screenPTROff2,fore_col, concatenatedSplines);
if Pstruct.useBubbles == 1
    Screen('PutImage',screenPTROff2,mask);
end