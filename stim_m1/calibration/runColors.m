screens=Screen('Screens');
screenNumber=max(screens);
mults=8;
[w, rect] = Screen('OpenWindow', screenNumber, [],[],[],[],[],mults,[]);

colmat=round(linspace(0,255,20));


for c=1:3
    for i=1:length(colmat)
        
        cm=[0 0 0];
        cm(c)=colmat(i);
        
        Screen(w, 'FillRect', cm);

        Screen(w, 'Flip');

        pause;
    end
end


KbWait;
Screen('CloseAll');


