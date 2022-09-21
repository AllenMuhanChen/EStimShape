function makeTexture_Img

%loads images, and scrambles if selected

global screenPTR Gtxtr IDim

if ~isempty(Gtxtr)
    Screen('Close',Gtxtr);  %First clean up: Get rid of all textures/offscreen windows
end

Gtxtr = [];

%get parameters
P = getParamStruct;

%read image
img=imread([P.repopath '/' P.imgbase1 '/' P.imgbase2 '/' num2str(P.imgnr) '.png']);
img=double(img);

%make output image
imgout=img;

IDim=size(imgout);

%generate texture
Gtxtr = Screen(screenPTR, 'MakeTexture', imgout);
