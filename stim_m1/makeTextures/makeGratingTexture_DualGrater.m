function makeGratingTexture_DualGrater

%This one builds only the images that get played for this trial.
%Importantly, this one doesn't allow for drift or contrast reversal like
%the old version in the 'archive' file.

global Mstate screenNum loopTrial %movieBlock

global Gtxtr TDim Mtxtr %'playgrating' will use these

Screen('Close')  %First clean up: Get rid of all textures/offscreen windows

Gtxtr = []; TDim = []; Mtxtr =[]; %reset

P = getParamStruct;

screenRes = Screen('Resolution',screenNum);
pixpercmX = screenRes.width/Mstate.screenXcm;
pixpercmY = screenRes.height/Mstate.screenYcm;

%The following gives inaccurate spatial frequencies
% xN = 2*Mstate.screenDist*tan(P.x_size/2*pi/180);  %grating width in cm
% xN = round(xN*pixpercmX);  %grating width in pixels
% yN = 2*Mstate.screenDist*tan(P.y_size/2*pi/180);  %grating height in cm
% yN = round(yN*pixpercmY);  %grating height in pixels

%The following assumes the screen is curved
xcm = 2*pi*Mstate.screenDist*P.x_size/360;  %stimulus width in cm
xN = round(xcm*pixpercmX);  %stimulus width in pixels
ycm = 2*pi*Mstate.screenDist*P.y_size/360;   %stimulus height in cm
yN = round(ycm*pixpercmY);  %stimulus height in pixels

%make aperture for stimulus once
xdom = linspace(-P.x_size/2,P.x_size/2,xN);
ydom = linspace(-P.y_size/2,P.y_size/2,yN);
[xdom ydom] = meshgrid(xdom,ydom);
r = sqrt(xdom.^2 + ydom.^2);
stimmask = zeros(size(r));
id = find(r<=P.mask_radius);
stimmask(id) = 1;


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%Create Sequence for this trial%%%%%

%Make spatial phase domain
phasedom = linspace(0,360,P.n_phase+1);
phasedom = phasedom(1:end-1);
%Make orientation domain
orirange = 180;
oridom = linspace(P.ori,P.ori+orirange,P.n_ori+1);
oridom = oridom(1:end-1);
%Make spatial frequency domain
if strcmp(P.sf_domain,'log')
    sfdom = logspace(log10(P.min_sf),log10(P.max_sf),P.n_sfreq);
elseif strcmp(P.sf_domain,'lin')
    sfdom = linspace(P.min_sf,P.max_sf,P.n_sfreq);
end
sfdom = unique(sfdom);

colordom = getColorDomain(P.colorspace);

maskdom=[1:P.CFSn_mask];


N_Im = round(P.stim_time*screenRes.hz/P.h_per); %number of images to present
Nframes=N_Im*P.h_per;

N_ImMask = ceil(Nframes/P.CFSh_per); %number of masks to present

s = RandStream.create('mrg32k3a','NumStreams',1,'Seed',P.rseed);
phaseseq = randi(s,[1 length(phasedom)],1,N_Im); %N_Im random indices for the "mixed bag"
oriseq = randi(s,[1 length(oridom)],1,N_Im); %N_Im random indices for the "mixed bag"
sfseq = randi(s,[1 length(sfdom)],1,N_Im); %N_Im random indices for the "mixed bag"
colorseq = randi(s,[1 length(colordom)],1,N_Im); %N_Im random indices for the "mixed bag"

maskseq = randi(s,[1 length(maskdom)],1,N_ImMask); %N_Im random indices

blankflag = zeros(1,N_Im);
if P.blankProb > 0
    nblanks = round(P.blankProb*N_Im);
    bidx = zeros(1,N_Im);    
    bidx(1:nblanks) = 1;
    dum = randn(1,N_Im);
    [dum id] = sort(dum);
    bidx = find(bidx(id));  %randomly shuffle
    
    %blank condition is identified with the following indices
    phaseseq(bidx) = 1;
    oriseq(bidx) = 1;
    sfseq(bidx) = length(sfdom) + 1;
    colorseq(bidx) = 1;
    
    blankflag(bidx) = 1;
end
    

for i = 1:N_Im    %loop through each image in the sequence
    if ~blankflag(i) & P.CFSstim_bit
        %Compression: Change zoom based on spatial frequency in x/y dimensions
        %independently.  Spatial frequency along x/y dimensions are modulated
        %by the grating's orientation.
        Xcycperimage = sfdom(sfseq(i))*P.x_size * abs(cos(oridom(oriseq(i))*pi/180));
        Ycycperimage = sfdom(sfseq(i))*P.y_size * abs(sin(oridom(oriseq(i))*pi/180));
        xNp = min([25*Xcycperimage+1 xN]); %No point in having the resolution higher than the screen
        yNp = min([25*Ycycperimage+1 yN]);
        
        x_ecc = P.x_size/2;
        y_ecc = P.y_size/2;
        
        x_ecc = single(linspace(-x_ecc,x_ecc,xNp));  %deg
        y_ecc = single(linspace(-y_ecc,y_ecc,yNp));
        
        [x_ecc y_ecc] = meshgrid(x_ecc,y_ecc);  %deg
        
        Im = buildImage(oridom(oriseq(i)),sfdom(sfseq(i)),phasedom(phaseseq(i)),x_ecc,y_ecc,P); %Make the shape
        putinTexture(Im,colordom,colorseq(i),P,i,stimmask); %Put in texture as RGB
       
    else
        putinTexture(0,colordom,colorseq(i),P,i,stimmask); %Blank
    end
end

if exist('Im','var')
    TDim = size(Im);
else
    TDim = [1 1];
end

for i = 1:N_ImMask    %loop through each image in the sequence
    %add mask
    maskTexture(maskseq(i),P,i);
end



%Save it if 'running' experiment
if Mstate.running
    Pseq = struct;
    Pseq.phaseseq = phaseseq;
    Pseq.oriseq = oriseq;
    Pseq.sfseq = sfseq;
    Pseq.colorseq = colorseq;
    Pseq.maskseq=maskseq;
    
    domains = struct;
    domains.oridom = oridom;
    domains.sfdom = sfdom;
    domains.phasedom = phasedom;
    domains.colordom = colordom;
    domains.maskdom=maskdom;
    
    %This version of 'saveLog' comes from the old code, where I would call
    %it from 2 places (the make/play files).  It no longer needs the
    %varargin input structure, but I just kept it out of consistency (and laziness).
    if loopTrial == 1
        saveLog(domains)
    end
    saveLog(Pseq,P.rseed)  %append log file with the latest sequence
    
    
end


function temp = buildImage(ori,sfreq,phase,x_ecc,y_ecc,P)


sdom = x_ecc*cos(ori*pi/180) - y_ecc*sin(ori*pi/180);    %deg
sdom = sdom*sfreq*2*pi + pi; %radians
temp = cos(sdom - phase*pi/180);  

switch P.s_profile
    
    case 'sin'
        temp = temp*P.contrast/100;
        
    case 'square'
        thresh = cos(P.s_duty*pi);
        temp = sign(temp-thresh);
        temp = temp*P.contrast/100;
        
    case 'pulse'
        thresh = cos(P.s_duty*pi);
        temp = (sign(temp-thresh) + 1)/2;
        temp = temp*P.contrast/100;
        
end


function putinTexture(Im,colordom,colorID,P,i,mask)

global Gtxtr screenPTRStereo StimAperture

%%%%%%%%%%%%%%%%%%%%%%%
%This is a total hack%%
if strcmp(P.colorspace,'DKL')
    switch colordom(colorID)
        case 4 %S
            Im = Im*.15/.82;
        case 5 %L-M
            Im = Im;
        case 6 %L+M
            Im = Im*.15/1.0;
    end
elseif strcmp(P.colorspace,'LMS')
    switch colordom(colorID)
        case 2 %L
            Im = Im;
        case 3 %M
            Im = Im*.2/.23;
        case 4 %S
            Im = Im*.2/.82;
    end
end
%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%

Idraw = ImtoRGB(Im,colordom(colorID),P,[]);
Gtxtr(i) = Screen(screenPTRStereo, 'MakeTexture', Idraw);

maskblob = P.background*ones([size(mask) 2]);
maskblob(:,:,2) = 255*(1-mask);
StimAperture = Screen(screenPTRStereo, 'MakeTexture', maskblob);


function maskTexture(maskID,P,i)

global Mtxtr screenPTRStereo

if P.CFSmask_bit==1
    img=imread(['/CSF_masks/' P.CFSmask_type '/CSFmask_' num2str(maskID) '.tif']);
    
    
    dimImg=size(img);

    xdom = linspace(-P.CFSx_size/2,P.CFSx_size/2,dimImg(2));
    ydom = linspace(-P.CFSy_size/2,P.CFSy_size/2,dimImg(1));
    [xdom ydom] = meshgrid(xdom,ydom);
    r = sqrt(xdom.^2 + ydom.^2);
    mask = zeros(size(r));
    id = find(r>=P.CFSin_radius & r<=P.CFSout_radius);
    mask(id) = 1;
    
    img(:,:,4)=mask*255;

    Mtxtr(i) = Screen(screenPTRStereo, 'MakeTexture', img);
else
    %val=[P.background P.background P.background 255];
    Mtxtr(i) = Screen(screenPTRStereo, 'MakeTexture', P.background);
end

