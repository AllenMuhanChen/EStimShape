def low_pass_filter(x, y, alpha):
    return alpha * x + (1 - alpha) * y

low_pass_result_1 = low_pass_filter(0, 0, 0.5)
low_pass_result_2 = low_pass_filter(low_pass_result_1, 1, 0.5)
low_pass_result_3 = low_pass_filter(low_pass_result_2, 2, 0.5)
low_pass_result_4 = low_pass_filter(low_pass_result_3, 3, 0.5)
low_pass_result_5 = low_pass_filter(low_pass_result_4, 4, 0.5)

print(low_pass_result_1)
print(low_pass_result_2)
print(low_pass_result_3)
print(low_pass_result_4)
print(low_pass_result_5)






