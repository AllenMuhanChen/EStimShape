function f = RandomSpike (taskId)
    input = int64(taskId)
    rand('state',sum(100*clock))
    f = 50 + rand * 50
end