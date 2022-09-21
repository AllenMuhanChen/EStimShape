function makeGrating_Ramp

%make one cycle of the grating

global Mstate screenPTR screenNum %movieBlock

global Gtxtr TDim  %'playgrating' will use these

Screen('Close')  %First clean up: Get rid of all textures/offscreen windows

Gtxtr = []; TDim = [];  %reset

P = getParamStruct;
screenRes = Screen('Resolution',screenNum);

pixpercmX = screenRes.width/Mstate.screenXcm;
pixpercmY = screenRes.height/Mstate.screenYcm;

    
%The following assumes the screen is curved
xcm = 2*pi*Mstate.screenDist*P.x_size/360;  %stimulus width in cm
xN = round(xcm*pixpercmX);  %stimulus width in pixels
ycm = 2*pi*Mstate.screenDist*P.y_size/360;   %stimulus height in cm
yN = round(ycm*pixpercmY);  %stimulus height in pixels
    

xN = round(xN/P.x_zoom);  %Downsample for the zoom
yN = round(yN/P.y_zoom);

%create the mask
xdom = linspace(-P.x_size/2,P.x_size/2,xN);
ydom = linspace(-P.y_size/2,P.y_size/2,yN);
[xdom ydom] = meshgrid(xdom,ydom);
r = sqrt(xdom.^2 + ydom.^2);
if strcmp(P.mask_type,'disc')
    mask = zeros(size(r));
    id = find(r<=P.mask_radius);
    mask(id) = 1;
elseif strcmp(P.mask_type,'gauss')
    mask = exp((-r.^2)/(2*P.mask_radius^2));
else
    mask = [];
end
mask = single(mask);
%%%%%%%%%

%%%%%%
%%%%%%BETA VERSION
[sdom tdom x_ecc y_ecc] = makeGraterDomain_beta(xN,yN,P.ori,P.s_freq,P.t_period,P.altazimuth);%orig


framesPerContrast=ceil(P.stim_time*screenRes.hz/(P.Ncontrast*2-1));

nrframes=framesPerContrast*(P.Ncontrast*2-1);

frameContrast=zeros(nrframes,1);
cvec=linspace(P.contrast_min,P.contrast_max,P.Ncontrast);
%disp(cvec)
cvec=[cvec fliplr(cvec(1:end-1))];
%disp(cvec)

for i=1:2*P.Ncontrast-1
    frameContrast((i-1)*framesPerContrast+1:i*framesPerContrast)=cvec(i);
end


for n=1:nrframes

    idx=mod(n-1,length(tdom))+1;
    Im = makePerGratFrame_Ramp(sdom,tdom,idx,frameContrast(n)); 
    
    ImRGB = ImtoRGB(Im,P.colormod,P,mask);
    
    Gtxtr(n) = Screen(screenPTR, 'MakeTexture', ImRGB);
    
end


TDim = size(ImRGB(:,:,1));
TDim(3) = framesPerContrast;



