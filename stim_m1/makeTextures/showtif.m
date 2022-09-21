screens=Screen('Screens');
screenNumber=max(screens);
[w, rect] = Screen('OpenWindow', screenNumber, 0);

Screen('BlendFunction', w, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

img=imread('/animal pics/Image0-10.tif');
img=mean(img,3);

%scrambling with blocks
nrblocks=8;
trialno=1;

s = RandStream.create('mrg32k3a','NumStreams',1,'Seed',datenum(date)+trialno);


imgdim=size(img);

sizeblockX=round(imgdim(1)/nrblocks);
sizeblockY=round(imgdim(2)/nrblocks);

blockstartX=[1:sizeblockX:imgdim(1)];
blockstopX=blockstartX+sizeblockX-1;
blockstopX(blockstopX>imgdim(1))=imgdim(1);

blockstartY=[1:sizeblockY:imgdim(2)];
blockstopY=blockstartY+sizeblockY-1;
blockstopY(blockstopY>imgdim(2))=imgdim(2);

[blockIdX,blockIdY]=meshgrid(1:nrblocks);


randvec=randperm(s,nrblocks.^2);

blockIdXrand=blockIdX(randvec);
blockIdYrand=blockIdY(randvec);

imgrand=zeros(size(img));
for i=1:nrblocks^2
    xin(1)=blockstartX(blockIdXrand(i));
    xin(2)=blockstopX(blockIdXrand(i));
    xout(1)=blockstartX(blockIdX(i));
    xout(2)=blockstopX(blockIdX(i));
    
    yin(1)=blockstartY(blockIdYrand(i));
    yin(2)=blockstopY(blockIdYrand(i));
    yout(1)=blockstartY(blockIdY(i));
    yout(2)=blockstopY(blockIdY(i));

    imgrand(xout(1):xout(2),yout(1):yout(2))=img(xin(1):xin(2),yin(1):yin(2));
end

contrast=100;
img=img*contrast/100;

Gtxtr = Screen(w, 'MakeTexture', img);
Screen(w, 'FillRect',128)
Screen('DrawTexture', w, Gtxtr,[],[100 100 600 600]);
Screen(w, 'Flip');

KbWait;
Screen('CloseAll');

