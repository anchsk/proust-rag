test:
what does the narrator feel about Françoise?
classify_intent: returns "semantic" as expected
run_pipeline returns : (id, distance)
[('ch3_p50_s8_c0', 0.24471890926361084), ('ch1_p213_s0_c0', 0.25600534677505493), ('ch1_p77_s2_c0', 0.2898181676864624), ('ch1_p212_s1_c0', 0.303230881690979), ('ch1_p60_s1_c0', 0.319230318069458)]

the chunks are far for the question above

and it's good match for the question below. however the distance is almost identical. how is it possible?

test:
cosa cucinava Françoise?
returns (id, distance):
[('ch1_p261_s0_c0', 0.25737738609313965), ('ch3_p50_s8_c0', 0.3066467046737671), ('ch1_p213_s0_c0', 0.32244956493377686), ('ch1_p212_s1_c0', 0.3510277271270752), ('ch1_p90_s0_c0', 0.3526439666748047)]