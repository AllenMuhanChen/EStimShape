function mm = sbxreadmmap(fname,varargin)

d = dir([fname '.sbx']);
if nargin >1 
    ext = varargin{1};
else
    ext = '';
end

i = load(fname);
switch(i.info.channels)
    case 1
        nchan = 2;
    case 2
        nchan = 1;
    case 3
        nchan = 1;
end

max_idx = d.bytes / prod(i.info.sz) / 2 / nchan;

mm = memmapfile([fname ext '.sbx'],'Format',{'uint16' [nchan 796 512 max_idx] 'img'},'Repeat',1,'Writable',true);