function makeV4Texture

%this is based on a gallant paper (Hansen et al, J Neurosci 2007)
%it contains a number of gratings (either spiral or hyperbolic), with
%random size, color, position, spatial frequency and velocity

global loopTrial screenPTR screenNum Gtxtr;


Screen('Close')  %First clean up: Get rid of all textures/offscreen windows
Gtxtr = [];   %reset



P = getParamStruct;


%initialize random number generate to time of date
s = RandStream.create('mrg32k3a','NumStreams',1,'Seed',datenum(date)+loopTrial);

%get screen parameters
screenRes = Screen('Resolution',screenNum);
fps=screenRes.hz;      % frames per second

%stimulus size
imgsize=[P.x_size P.y_size];


%sizes go as power of two
pow2max=round(log2(P.maxsize));
pow2min=round(log2(P.minsize));
nrsizes=pow2max-pow2min+1;
sizevec=2^pow2max./(2.^[0:nrsizes-1]);
sizevec=sizevec/2;

%nr of gratings per size goes in reverse to the size
nrvec=2.^[0:nrsizes-1];
nrvec=nrvec*P.grdensity; %adjust to get correct density
nrgratings=sum(nrvec); %this is the number per type

if P.contrast==0
    nrgratings=0;
end

%get a vector with the size for each grating
grsizeidx=[];
for i=1:nrsizes
    grsizeidx=[grsizeidx;repmat(i,nrvec(i),1)];
end

%locations - try to somewhat evenly distribute the locations
[xposscreen yposscreen]=meshgrid(1:imgsize(1),1:imgsize(2));
posidx=randi(s,length(xposscreen(:)),nrgratings,2);
xpos=xposscreen(posidx);
ypos=yposscreen(posidx);

%initial phase
grphase=rand(s,nrgratings,2)*2*pi;

%velocity
grvel=(rand(s,nrgratings,2)*(P.maxvel-P.minvel)+P.minvel)*2*pi;

%color
if P.colorbit==1
    colmat=randi(s,2,nrgratings,3,2)-1;
else
    colmat=ones(nrgratings,3,2);
end

%spatial frequency
%for the radial frequency for the spiral, as well as the frequency for the hyperbolic
%randomly choose a number between 1/mincycle and 1/maxcycle
sfreq=rand(s,nrgratings,2)*(1/P.maxcyc-1/P.mincyc)+1/P.mincyc;


%for the spiral, also need concentric frequency; minimum needs to be 1
%(otherwise get line in image)
%limits are otherwise pretty arbitrary
cfreq=randi(s,P.maxconc,nrgratings);


%spiral gratings also need direction
dirspiral=randi(s,2,nrgratings);
dirspiral(find(dirspiral==2))=-1;

%hyperbolic gratings need orientation
orihyp=randi(s,180,nrgratings);


%make grids
for i=1:nrsizes
    xtmp=[-sizevec(i):sizevec(i)];
    ytmp=[-sizevec(i):sizevec(i)];
    [xtmp ytmp]=meshgrid(xtmp,ytmp);
    xcoord{i}=xtmp;
    ycoord{i}=ytmp;
    [thetatmp,rhotmp]=cart2pol(xtmp,ytmp);
    thetacoord{i}=thetatmp;
    rhocoord{i}=rhotmp;
    masktmp = exp((-rhotmp.^2)/((sizevec(i)/2)^2));
    mask{i}=(masktmp-min(masktmp(:)))/(max(masktmp(:))-min(masktmp(:)));
end


nrframes=ceil(P.stim_time*fps);

%add gratings
for f=1:nrframes
    colmask=zeros(imgsize(2),imgsize(1),3);

    for i=1:nrgratings
        
        s=grsizeidx(i);
        
        for j=1:2 %stimtype
            
            if j==1 %add a spiral
                stim=cos(cfreq(i)*thetacoord{s} + dirspiral(i)*2*pi*rhocoord{s}*sfreq(i,1) + ...
                    grphase(i,j)+(f-1)*grvel(i,j));
            else %add a hyperbolic grating
                udom=xcoord{s}*cos(orihyp(i)*pi/180) - ycoord{s}*sin(orihyp(i)*pi/180);
                vdom=xcoord{s}*sin(orihyp(i)*pi/180) + ycoord{s}*cos(orihyp(i)*pi/180);
                sdom=sqrt(abs(udom.*vdom));
                stim=cos(2*pi*sfreq(i,2)*sdom + grphase(i,j)+(f-1)*grvel(i,j));
            end
            
            
            %mask with gaussian
            stim=stim.*mask{s};
            
           
            %crop image correctly before putting it into the main matrix
            if xpos(i,j)-sizevec(s)<1
                xin(1)=abs(xpos(i,j)-sizevec(s))+2;
            else
                xin(1)=1;
            end
            if xpos(i,j)+sizevec(s)>imgsize(1)
                xin(2)=2*sizevec(s)+1-(xpos(i,j)+sizevec(s)-imgsize(1));
            else
                xin(2)=2*sizevec(s)+1;
            end
            
            if ypos(i,j)-sizevec(s)<1
                yin(1)=abs(ypos(i,j)-sizevec(s))+2;
            else
                yin(1)=1;
            end
            if ypos(i,j)+sizevec(s)>imgsize(2)
                yin(2)=2*sizevec(s)+1-(ypos(i,j)+sizevec(s)-imgsize(2));
            else
                yin(2)=2*sizevec(s)+1;
            end
            
            
            xout(1)=max(1,xpos(i,j)-sizevec(s));
            xout(2)=min(imgsize(1),xpos(i,j)+sizevec(s));
            yout(1)=max(1,ypos(i,j)-sizevec(s));
            yout(2)=min(imgsize(2),ypos(i,j)+sizevec(s));
            
            
            for c=1:3
                colmask(yout(1):yout(2),xout(1):xout(2),c)=...
                    colmask(yout(1):yout(2),xout(1):xout(2),c)+...
                    stim(yin(1):yin(2),xin(1):xin(2)).*colmat(i,c,j);
            end
            
            
        end %for stimtype
    end %for grating
    
    colmask(colmask>1)=1;
    colmask(colmask<-1)=-1;
    colmask=(colmask+1)/2;
    colmask=round(colmask*255);
    
    
    Gtxtr(f) = Screen(screenPTR, 'MakeTexture', colmask);
end
