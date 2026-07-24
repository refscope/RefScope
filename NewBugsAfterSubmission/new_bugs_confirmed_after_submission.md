## The bugs listed here were newly confirmed after the submission of the paper, and we will continue to update this list.

| id | buggy function | file path | line number | bug type | get_functions | put_functions |
|-------|---------|-----------|-------------|----------|---------------|---------------|
| 1 | ingenic_register_clock | drivers/clk/ingenic/cgu.c | 784 | refcount leak | clk_register | clk_put |
| 2 | aries_audio_probe | sound/soc/samsung/aries_wm8994.c | 686 | double put | of_node_get | of_node_put |
| 3 | chcr_aes_encrypt | drivers/crypto/chelsio/chcr_algo.c | 1375 | refcount leak | chcr_inc_wrcount | chcr_dec_wrcount |
