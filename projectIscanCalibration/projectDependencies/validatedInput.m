function ip = validatedInput(msg,allOutcomes)
    ip = [];
    
    while 1
        try 
            ip = input(msg);
            if isempty(ip) || sum(allOutcomes == ip) == 0
                disp('Invalid input. Try again.');
            else
                break;
            end
        catch
            disp('Invalid input. Try again.');
        end
    end
end