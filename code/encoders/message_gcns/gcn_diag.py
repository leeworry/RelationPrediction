import numpy as np
import tensorflow as tf

from encoders.message_gcns.message_gcn import MessageGcn


class DiagGcn(MessageGcn):

    def parse_settings(self):
        self.embedding_width = int(self.settings['InternalEncoderDimension'])
        self.dropout_keep_probability = float(self.settings['DropoutKeepProbability'])

    def local_initialize_train(self):
        vertex_feature_dimension = self.entity_count if self.onehot_input else self.embedding_width
        type_matrix_shape = (self.relation_count *2 + 1, self.embedding_width)
        vertex_matrix_shape = (vertex_feature_dimension, self.embedding_width)

        glorot_var_combined = np.sqrt(3/(vertex_matrix_shape[0] + vertex_matrix_shape[1]))
        type_init_var = 1

        vertex_projection_sender_initial = np.random.normal(0, glorot_var_combined, size=vertex_matrix_shape).astype(np.float32)
        type_initial = np.random.normal(0, type_init_var, size=type_matrix_shape).astype(np.float32)

        message_bias = np.zeros(self.embedding_width).astype(np.float32)

        self.V_proj_sender = tf.Variable(vertex_projection_sender_initial)
        self.V_types = tf.Variable(type_initial)
        self.B_message = tf.Variable(message_bias)

    def local_get_weights(self):
        return [self.V_proj_sender, self.V_types,
                self.B_message]

    def compute_messages(self, sender_features):
        sender_terms = self.dot_or_lookup(sender_features, self.V_proj_sender)
        message_types = self.get_graph().get_type_indices()
        type_diags = tf.nn.embedding_lookup(self.V_types, message_types)

        terms = tf.mul(sender_terms, type_diags)

        messages = terms
        return messages

    def sum_messages(self, messages):
        mtr = self.get_graph().incidence_matrix(normalization=('global', 'recalculated'))
        collected_messages = tf.sparse_tensor_dense_matmul(mtr, messages)
        return collected_messages + self.B_message