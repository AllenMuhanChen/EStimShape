
function r = sbxsegment(fn)

close all;

sbxread(fn,1,1);

global info;


% get the mag

if(isfield(info,'config'))
    mag = info.config.magnification;
    display(sprintf('Mag = x%d',mag));
else
    mag = 1;
    display(sprintf('Mag [default] = x%d',mag));
end

switch mag
    case 1
        W = 10;
    case 2
        W = 20;
    case 4
        W = 40;
end

% read data 

z = sbxread(fn,0,600);
% compute correlation map

z = double(squeeze(z));
global info

% align
for(i=1:600)
    z(:,:,i) = circshift(z(:,:,i),info.aligned.T(i,:));
end

%z = diff(z,1,3);

me = mean(z,3);
z = bsxfun(@minus,z,me);
va = mean(z.^2,3);
z = bsxfun(@rdivide,z,sqrt(va));
ku = mean(z.^4,3)-3;

corrmap = zeros([size(z,1) size(z,2)]);

for(m=-2:2)
    for(n=-2:2)
        if(m~=0 || n~=0)
            corrmap = corrmap+squeeze(sum(z.*circshift(z,[m n 0]),3));
        end
    end
end

v = corrmap;

% select points based on the variance

v(1:(4*W+1),:) = NaN;
v(end-(4*W+1):end,:)=NaN;
v(:,1:(4*W+1)) = NaN;
v(:,end-(4*W+1):end)=NaN;

% load('-mat',[fn '.align']);

imagesc(v); truesize; colormap gray;

nroi = 50;
P = zeros(nroi,2);
for(k=1:nroi)
    [i,j] = find(v==max(v(:)));
    P(k,:) = [i j];
    v(i-10:i+10,j-10:j+10) = NaN;
    hold on
    plot(j,i,'r.');
end
hold off

% [xx,yy] = meshgrid(51:50:size(v,2)-51,51:50:size(v,1)-51);
% P = [yy(:) xx(:)];

%

% segmenting

clear plist;

h = waitbar(0,'Segmenting') ;
for(i=1:size(P,1))
     waitbar(i/size(P,1),h);
     s = z(P(i,1)-W:P(i,1)+W,P(i,2)-W:P(i,2)+W,:);
     plist{i} = sbxsegmentsub(s,200,5,mag);
end
delete(h);

% put it together...

display('Merging...')

seg = zeros(size(v));
kcell=0;
for(i=1:size(P,1))
    pl = plist{i};
    for(j=1:length(pl))
        pidx = pl{j};
        pidx = [pidx(:,2) pidx(:,1)];
        pidx = ones(size(pidx,1),1)*(P(i,:)- [(W+1) (W+1)])+pidx;
        jj = sub2ind(size(seg),pidx(:,1),pidx(:,2));
        kcell = kcell+1;
        for(k=1:length(jj))
            if(seg(jj)==0)
                seg(jj)= kcell;
            end
        end
    end
end

% contraints at the end...

cc = regionprops(seg,'Area','Solidity','PixelIdxList','Eccentricity','PixelList');

r = zeros(size(seg));

k=0;
for(j=1:length(cc))
    if(cc(j).Area<700*mag^2 && cc(j).Area>100*mag^2 && cc(j).Solidity>0.82 && cc(j).Eccentricity<0.9)
        r(cc(j).PixelIdxList) = k;
        k = k+1;
    end
end

clf
imshow(label2rgb(r,'jet','k','shuffle'))

