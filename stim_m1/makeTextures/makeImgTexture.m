function makeImgTexture


global screenPTR Gtxtr loopTrial IDim;


Screen('Close')  %First clean up: Get rid of all textures/offscreen windows
Gtxtr = [];   %reset


%get parameters
Pstruct = getParamStruct;


%read image
img=imread(['/' Pstruct.imgpath '/' Pstruct.imgbase num2str(Pstruct.imgcat) '-' num2str(Pstruct.imgnr) '.tif']);

%turn into black and white image
img=mean(img,3);

%make output image
imgout=img;


%if selected, scramble the image by reordering blocks
if Pstruct.scramble==1
    s = RandStream.create('mrg32k3a','NumStreams',1,'Seed',datenum(date)+loopTrial);
    
    %get size of the blocks
    imgdim=size(img);
    sizeblockX=round(imgdim(1)/Pstruct.nrblocks);
    sizeblockY=round(imgdim(2)/Pstruct.nrblocks);
    
    %make sure that the blocks actually fit (may have to adjust the image size
    %a little bit)
    img=imresize(img,[sizeblockX*Pstruct.nrblocks sizeblockY*Pstruct.nrblocks]);
    
    %get start and stop pixels for every block
    blockstartX=[1:sizeblockX:imgdim(1)];
    blockstopX=blockstartX+sizeblockX-1;
    blockstopX(blockstopX>imgdim(1))=imgdim(1);
    
    blockstartY=[1:sizeblockY:imgdim(2)];
    blockstopY=blockstartY+sizeblockY-1;
    blockstopY(blockstopY>imgdim(2))=imgdim(2);
    
    %get IDs for every block
    [blockIdX,blockIdY]=meshgrid(1:Pstruct.nrblocks);
    
    %randomize block order
    randvec=randperm(s,Pstruct.nrblocks.^2);
    blockIdXrand=blockIdX(randvec);
    blockIdYrand=blockIdY(randvec);
    
    %make scrambled images
    for i=1:Pstruct.nrblocks^2
        xin(1)=blockstartX(blockIdXrand(i));
        xin(2)=blockstopX(blockIdXrand(i));
        xout(1)=blockstartX(blockIdX(i));
        xout(2)=blockstopX(blockIdX(i));
        
        yin(1)=blockstartY(blockIdYrand(i));
        yin(2)=blockstopY(blockIdYrand(i));
        yout(1)=blockstartY(blockIdY(i));
        yout(2)=blockstopY(blockIdY(i));
        
        imgout(xout(1):xout(2),yout(1):yout(2))=img(xin(1):xin(2),yin(1):yin(2));
    end
end

c=Pstruct.contrast/100;
imgout=imgout.*c+Pstruct.background*(1-c);

IDim=size(imgout);

%generate texture
Gtxtr = Screen(screenPTR, 'MakeTexture', imgout);


