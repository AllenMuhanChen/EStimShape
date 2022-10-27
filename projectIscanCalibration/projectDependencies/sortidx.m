function idx = sortidx(a,opt1,opt2,opt3,opt4)
    if exist('opt4','var')
        [~,idx] = sort(a,opt1,opt2,opt3,opt4);
    elseif exist('opt2','var')
        [~,idx] = sort(a,opt1,opt2);
    elseif exist('opt1','var')
        [~,idx] = sort(a,opt1);
    else
        [~,idx] = sort(a);
    end
end