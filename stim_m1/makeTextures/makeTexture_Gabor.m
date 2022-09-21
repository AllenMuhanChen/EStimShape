function makeTexture_Gabor

%loads images, and scrambles if selected

global screenPTR Gtxtr IDim
Screen(screenPTR,'BlendFunction',GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

if ~isempty(Gtxtr)
    Screen('Close',Gtxtr);  %First clean up: Get rid of all textures/offscreen windows
end

%get parameters
P = getParamStruct;

% create gabor and save it in a temp image file
param.pos = [0 0];
param.ori = deg2rad(P.ori);
param.sw = P.sw;
param.phase = deg2rad(P.phase);
param.siz = 1; % don't adjust size in the image
param.cont = P.cont;
param.aRatio = P.aRatio;
param.col = [getCol(P.col1); getCol(P.col2)];

nPix = [640 480];
[x,y] = meshgrid(linspace(-4*pi,4*pi,nPix(1)),linspace(-3*pi,3*pi,nPix(2)));
[gb,al] = getGabor(param,x,y);

imwrite(gb,'/stimulator_slave/makeTextures/utils/temp_img.png','Background',[0.5 0.5 0.5],'Alpha',al);


%read image
[img,~,al]=imread('/stimulator_slave/makeTextures/utils/temp_img.png');
img=double(cat(3,img,al));

%make output image
imgout=img;

IDim=size(imgout);

%generate texture
Gtxtr = Screen(screenPTR, 'MakeTexture', imgout);

end

function col = getCol(id)
    switch(id)
        case 1 % k
            col = [0.001 0.001 0.001];
        case 2 % r
            col = [1 0.25 0.25];
        case 3 % g
            col = [0.25 1 0.25];
        case 4 % b
            col = [0.25 0.25 1];
        case 5 % y
            col = [0.75 0.75 0];
        case 6 % c
            col = [0 0.75 0.75];
        case 7 % m
            col = [0.75 0 0.75];
        case 8 % w
            col = [1 1 1];
    end
end
