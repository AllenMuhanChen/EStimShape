DELETE FROM TaskToDo
WHERE task_id NOT IN (
    SELECT task_id FROM TaskDone
    WHERE part_done = 0
);