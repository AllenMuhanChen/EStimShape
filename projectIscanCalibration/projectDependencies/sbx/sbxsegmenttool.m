function varargout = sbxsegmenttool(varargin)
% SBXSEGMENTTOOL MATLAB code for sbxsegmenttool.fig
%      SBXSEGMENTTOOL, by itself, creates a new SBXSEGMENTTOOL or raises the existing
%      singleton*.
%
%      H = SBXSEGMENTTOOL returns the handle to a new SBXSEGMENTTOOL or the handle to
%      the existing singleton*.
%
%      SBXSEGMENTTOOL('CALLBACK',hObject,eventData,handles,...) calls the local
%      function named CALLBACK in SBXSEGMENTTOOL.M with the given input arguments.
%
%      SBXSEGMENTTOOL('Property','Value',...) creates a new SBXSEGMENTTOOL or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before sbxsegmenttool_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property application
%      stop.  All inputs are passed to sbxsegmenttool_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help sbxsegmenttool

% Last Modified by GUIDE v2.5 22-May-2017 16:49:09

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @sbxsegmenttool_OpeningFcn, ...
                   'gui_OutputFcn',  @sbxsegmenttool_OutputFcn, ...
                   'gui_LayoutFcn',  [] , ...
                   'gui_Callback',   []);
if nargin && ischar(varargin{1})
    gui_State.gui_Callback = str2func(varargin{1});
end

if nargout
    [varargout{1:nargout}] = gui_mainfcn(gui_State, varargin{:});
else
    gui_mainfcn(gui_State, varargin{:});
end
% End initialization code - DO NOT EDIT


% --- Executes just before sbxsegmenttool is made visible.
function sbxsegmenttool_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to sbxsegmenttool (see VARARGIN)

% Choose default command line output for sbxsegmenttool
handles.output = hObject;

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes sbxsegmenttool wait for user response (see UIRESUME)
% uiwait(handles.figure1);


axes(handles.axz);
global zimg hline vline
zimg = imagesc(zeros(512,796,3,'uint8'));
hold on
hline = plot([ 0 0],[0 0],'m--');
vline = plot([0 0 ],[0 0],'m--');
colormap gray
axis off
hold off


axes(handles.ax);
global bgimg
bgimg = imagesc(zeros(512,796,3,'uint8'));
colormap gray
axis off


% --- Outputs from this function are returned to the command line.
function varargout = sbxsegmenttool_OutputFcn(hObject, eventdata, handles) 
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;

% --- Executes on button press in load.
function load_Callback(hObject, eventdata, handles)
% hObject    handle to load (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

global oldcmap bgimg roimask data segmenttool_h nframes ncell cellpoly mask rfn pathname

roimask = [];

handles.status.String = 'Resetting/Clearing GPU';
drawnow;
gpuDevice(1);

handles.cellsel.String = {'Cell #'};
handles.cellsel.Enable = 'off';

global sig;
delete(handles.axes3.Children);
sig = [];

[fn,pathname] = uigetfile({'*_rigid*sbx; *_nonrigid*sbx'});
fn = [pathname fn];
rfn = strtok(fn,'.');
idx = max(strfind(rfn,'_'));
rfnx = rfn(1 : (idx-1));

try
    load('-mat',[rfnx '.align']); 
catch
    return
end
axis off

handles.status.String = 'Loading alignment data';

if(exist('mnr','var'))
    m = gather(mnr);
end

m = (m-min(m(:)))/(max(m(:))-min(m(:)));
x = adapthisteq(m);
x = single(x);
x = (x-min(x(:)))/(max(x(:))-min(x(:)));
bgimg.CData(:,:,1) = uint8(255*x);
bgimg.CData(:,:,2) = bgimg.CData(:,:,1);
bgimg.CData(:,:,3) = bgimg.CData(:,:,1);
 

if(~isempty(cellpoly))
    cellfun(@delete,cellpoly);
end

drawnow;

handles.status.String = 'Loading spatio-temporal data';

[rfn,~] = strtok(fn,'.');

z = sbxread(rfn,0,1);
global info;

nframes = str2double(handles.frames.String);
skip = floor(info.max_idx/nframes);

data = single(gpuArray(sbxreadskip(rfn,nframes,skip)));

% data = single(gpuArray(sbxread(rfn,round(info.max_idx/2-nframes/2),nframes)));
% data = squeeze(data(1,:,:,:));

data = zscore(data,[],3);

% remove trends
% 
% [N,M,T] = size(data);
% data = reshape(data,N*M,[]);
% data = detrend(data,1:50:T);
% data = reshape(data,N,M,T);


% compute and display correlation map...

handles.status.String = 'Computing correlation map';
drawnow;

corrmap = zeros([size(data,1) size(data,2)],'single','gpuArray');

for(m=-1:1)
    for(n=-1:1)
        if(m~=0 || n~=0)
            corrmap = corrmap+squeeze(sum(data.*circshift(data,[m n 0]),3));
        end
    end
end
corrmap = corrmap/8/size(data,3);

x = gather(corrmap);
x = (x-min(x(:)))/(max(x(:))-min(x(:)));
bgimg.CData(:,:,1) = uint8(255*x);
bgimg.CData(:,:,2) = uint8(0);
bgimg.CData(:,:,3) = uint8(0);

global zimg vline hline;
a = zimg.Parent;
%delete(a.Children(1:end-1));
idx = [];
for k = 1:length(a.Children)
    if(isa(a.Children(k),'matlab.graphics.primitive.Patch'))
        idx = [idx k];
    end
end
delete(a.Children(idx));

zimg.CData(:,:,1) = uint8(255*x);
zimg.CData(:,:,2) = uint8(255*x);
zimg.CData(:,:,3) = uint8(255*x);
set(zimg.Parent,'xlim',[size(x,2)/2-32 size(x,2)/2+32],'ylim',[size(x,1)/2 - 32 size(x,1)/2+32]);
set(hline,'xdata',[size(x,2)/2-32 size(x,2)/2+32],'ydata',size(x,1)/2 *[ 1 1]);
set(vline,'ydata',[size(x,1)/2-32 size(x,1)/2+32],'xdata',size(x,2)/2 *[ 1 1]);

% init

ncell = 0;
cellpoly = {};
oldcmap = {};
mask = zeros(size(data,1),size(data,2));

% previous segmentation?
if(exist([rfn '.segment'],'file'))
    load([rfn '.segment'],'-mat');
    drawnow;
    axes(bgimg.Parent);
    cellpoly = cell(1,length(vert));
    ncell = length(cellpoly);
    for i = 1:length(vert)
        cellpoly{i} = patch(vert{i}(:,1),vert{i}(:,2),'white','facecolor',[1 .7 .7], ...
            'facealpha',0.7,'edgecolor',[1 1 1],'parent',bgimg.Parent,'FaceLighting','none',...
            'userdata',i,'tag','apatch');
    end
    status.String = sprintf('Segmented %d cells from prior session',ncell);
end


drawnow;
set(segmenttool_h,'WindowButtonMotionFcn',@sbxwbmcb)
set(segmenttool_h,'WindowScrollWheelFcn',@sbxwswcb)
set(segmenttool_h,'WindowButtonDownFcn',@sbxwbdcb)

handles.status.String = 'Showing correlation map. Start segmenting';
   
% --- Executes on button press in save.
function save_Callback(hObject, eventdata, handles)
% hObject    handle to save (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

global rfn mask cellpoly pathname ncell

handles.status.String = sprintf('Saved %d cells in %s.segment',ncell,rfn);

if(handles.neuropil.Value)    
    np_mask = cell(ncell);
    q0 = imdilate(mask>0,strel('disk',round(0.15*str2double(handles.radius.String)),8));
    for(i=1:ncell)
        q =  imdilate(mask==i,strel('disk',str2double(handles.radius.String),8));
        q(q0>0) = 0;
        np_mask{i}=q;
    end
end

vert = cellfun(@(x) x.Vertices,cellpoly,'UniformOutput',false);

if(handles.neuropil.Value)
    save([rfn '.segment'],'mask','vert','np_mask');
else
    save([rfn '.segment'],'mask','vert');
end


function frames_Callback(hObject, eventdata, handles)
% hObject    handle to frames (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of frames as text
%        str2double(get(hObject,'String')) returns contents of frames as a double

global nframes
nframes = str2double(hObject.String);


% --- Executes during object creation, after setting all properties.
function frames_CreateFcn(hObject, eventdata, handles)
% hObject    handle to frames (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes during object creation, after setting all properties.
function ax_CreateFcn(hObject, eventdata, handles)
% hObject    handle to ax (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: place code in OpeningFcn to populate ax
% 
% global bgimg
% 
% bgimg = imagesc(zeros(512,796,3,'uint8'));
% colormap gray
% axis off
% set(hObject,'Tag','ax');


function nhood_Callback(hObject, eventdata, handles)
% hObject    handle to nhood (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of nhood as text
%        str2double(get(hObject,'String')) returns contents of nhood as a double

global nhood
nhood = str2double(hObject.String);


% --- Executes during object creation, after setting all properties.
function nhood_CreateFcn(hObject, eventdata, handles)
% hObject    handle to nhood (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
'NHOOD'
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes during object creation, after setting all properties.
function figure1_CreateFcn(hObject, eventdata, handles)
% hObject    handle to figure1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

global segmenttool_h frames th_corr zs ps
segmenttool_h = hObject;
zs = 0;
ps = 0;

frames = 300;
th_corr = 0.2;
   


% --- Executes during object creation, after setting all properties.
function bgimg_CreateFcn(hObject, eventdata, handles)
% hObject    handle to ax (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: place code in OpeningFcn to populate ax


% --- Executes during object creation, after setting all properties.
function status_CreateFcn(hObject, eventdata, handles)
% hObject    handle to status (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

global status

status = hObject;


% --- Executes on selection change in method.
function method_Callback(hObject, eventdata, handles)
% hObject    handle to method (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns method contents as cell array
%        contents{get(hObject,'Value')} returns selected item from method

global method segmenttool_h

method = hObject;

if(method.Value==3)
    set(segmenttool_h,'WindowButtonMotionFcn',[])
    set(segmenttool_h,'WindowScrollWheelFcn',[])
    set(segmenttool_h,'WindowButtonDownFcn',@sbxwbdcb_manual)
else
    set(segmenttool_h,'WindowButtonMotionFcn',@sbxwbmcb)
    set(segmenttool_h,'WindowScrollWheelFcn',@sbxwswcb)
    set(segmenttool_h,'WindowButtonDownFcn',@sbxwbdcb)
end



% --- Executes during object creation, after setting all properties.
function method_CreateFcn(hObject, eventdata, handles)
% hObject    handle to method (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function nhsize_Callback(hObject, eventdata, handles)
% hObject    handle to nhsize (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of nhsize as text
%        str2double(get(hObject,'String')) returns contents of nhsize as a double

global nhood 
nhood = str2double(hObject.String);


% --- Executes during object creation, after setting all properties.
function nhsize_CreateFcn(hObject, eventdata, handles)
% hObject    handle to nhsize (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

global  nhood_h
nhood_h = hObject;

% --- Executes on mouse press over figure background.
function figure1_ButtonDownFcn(hObject, eventdata, handles)
% hObject    handle to figure1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on selection change in popupmenu2.
function popupmenu2_Callback(hObject, eventdata, handles)
% hObject    handle to popupmenu2 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns popupmenu2 contents as cell array
%        contents{get(hObject,'Value')} returns selected item from popupmenu2


global segmenttool_h

switch get(hObject,'Value')
    case 1
        pan(segmenttool_h,'off');
        zoom(segmenttool_h,'off');
    case 2
        pan(segmenttool_h,'off');
        zoom(segmenttool_h,'on');
    case 3
        pan(segmenttool_h,'on');
        zoom(segmenttool_h,'off');
end





% --- Executes during object creation, after setting all properties.
function popupmenu2_CreateFcn(hObject, eventdata, handles)
% hObject    handle to popupmenu2 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

global mode_h

mode_h = hObject;



% --- Executes on button press in extract.
function extract_Callback(hObject, eventdata, handles)
% hObject    handle to extract (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

global rfn sig np spks
[sig,np,spks] = sbxpullsignals(rfn);
handles.status.String = sprintf('Signals extracted and saved for %s',rfn);
for(i=1:size(sig,2))
    handles.cellsel.String{i} = sprintf('Cell %d',i);
end
handles.cellsel.Enable = 'on';

% plot(handles.axes3,zscore(sig));
% handles.axes3.Visible = 'off';
% handles.axes3.YLim = [-0.5 10];
% handles.axes3.XLim = [1 size(sig,1)];

% --- Executes during object creation, after setting all properties.
function axes3_CreateFcn(hObject, eventdata, handles)
% hObject    handle to axes3 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: place code in OpeningFcn to populate axes3

axis off;


% --- Executes on button press in checkbox2.
function checkbox2_Callback(hObject, eventdata, handles)
% hObject    handle to checkbox2 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of checkbox2


% --- Executes during object creation, after setting all properties.
function axz_CreateFcn(hObject, eventdata, handles)
% hObject    handle to axz (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: place code in OpeningFcn to populate axz

% global zimg
% 
% zimg = imagesc(zeros(512,796,3,'uint8'));
% 
% colormap gray
% axis off
% set(hObject,'Tag','axz');

% 



function edit4_Callback(hObject, eventdata, handles)
% hObject    handle to edit4 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of edit4 as text
%        str2double(get(hObject,'String')) returns contents of edit4 as a double

global lambda 
lambda = str2double(hObject.String);


% --- Executes during object creation, after setting all properties.
function edit4_CreateFcn(hObject, eventdata, handles)
% hObject    handle to edit4 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

global  lambda_h
lambda_h = hObject;


% --- Executes on button press in undo.
function undo_Callback(hObject, eventdata, handles)
% hObject    handle to undo (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

global mask cellpoly ncell oldcmap bgimg

mask(mask == ncell) = 0;

ch = handles.ax.Children;
for(i=1:length(ch))
    if(ch(i).UserData==ncell)
        delete(ch(i));
        break;
    end
end

ch = handles.axz.Children;
for(i=1:length(ch))
    if(ch(i).UserData==ncell)
        delete(ch(i));
        break;
    end
end

% restore old map

r = oldcmap{ncell};
bgimg.CData(:,:,1) = r;    

ncell = ncell-1;


% --- Executes on button press in neuropil.
function neuropil_Callback(hObject, eventdata, handles)
% hObject    handle to neuropil (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of neuropil



function radius_Callback(hObject, eventdata, handles)
% hObject    handle to radius (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of radius as text
%        str2double(get(hObject,'String')) returns contents of radius as a double


% --- Executes during object creation, after setting all properties.
function radius_CreateFcn(hObject, eventdata, handles)
% hObject    handle to radius (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on selection change in cellsel.
function cellsel_Callback(hObject, eventdata, handles)
% hObject    handle to cellsel (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns cellsel contents as cell array
%        contents{get(hObject,'Value')} returns selected item from cellsel

global sig np spks cellpoly

idx = hObject.Value;
plot(handles.axes3,zscore(sig(:,idx)+4),'b','linewidth',1);
if(~isempty(np))
    hold(handles.axes3,'on');
    plot(handles.axes3,zscore(np(:,idx))-4,'color',[.5 .5 .5]);
    plot(handles.axes3,zscore(spks(:,idx))-8,'color',[1 .2 .2],'linewidth',1);
    hold(handles.axes3,'off');
end
handles.axes3.Visible = 'off';
handles.axes3.YLim = [-10 10];
handles.axes3.XLim = [1 size(sig,1)];
for(i=1:size(sig,2))
    if(cellpoly{i}.UserData == idx)
        cellpoly{i}.FaceColor = [0 1 0];
        cellpoly{i}.FaceAlpha = 1;
    else
        cellpoly{i}.FaceColor = [1 .7 .7];
        cellpoly{i}.FaceAlpha = .7;
    end
end





% --- Executes during object creation, after setting all properties.
function cellsel_CreateFcn(hObject, eventdata, handles)
% hObject    handle to cellsel (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in roi.
function roi_Callback(hObject, eventdata, handles)
% hObject    handle to roi (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

global roi roimask segmenttool_h bgimg

set(segmenttool_h,'WindowButtonMotionFcn',[])
set(segmenttool_h,'WindowScrollWheelFcn',[])
set(segmenttool_h,'WindowButtonDownFcn',[])


roi = imrect(handles.ax,[100 100 256 256]);
roi.setFixedAspectRatioMode(false);
wait(roi);
roimask = roi.createMask;
delete(roi);

r = single(bgimg.CData(:,:,1));
r = r.*roimask;
r = (r-min(r(:)))/(max(r(:))-min(r(:)));
bgimg.CData(:,:,1) = uint8(r*255);

drawnow;

set(segmenttool_h,'WindowButtonMotionFcn',@sbxwbmcb)
set(segmenttool_h,'WindowScrollWheelFcn',@sbxwswcb)
set(segmenttool_h,'WindowButtonDownFcn',@sbxwbdcb)
