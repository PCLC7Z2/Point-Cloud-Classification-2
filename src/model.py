import os
import numpy as np
import tensorflow as tf
from data_utils import get_filenames_and_class, generate_class_str_to_num_dict
from data_utils import get_points_and_class
from data_utils import remove_small_point_clouds
from random import shuffle
from datatime import datetime

class Model:
    def __init__(self, args):
        self.args = args
        self.train_list, self.test_list = get_filenames_and_class(args.Net10_data_dir)
        self.train_list = remove_small_point_clouds(self.train_list, self.args.small_sample_threshold)
        self.test_list = remove_small_point_clouds(self.test_list, self.args.small_sample_threshold)
        self.class_dict = generate_class_str_to_num_dict(args.Net10_data_dir)
        self.point_net = self.build_point_net()

    def build_point_net(self):
        n_dims = 3

        xavier_init = tf.contrib.layers.xavier_initializer_conv2d()

        self.X = tf.placeholder(tf.float32, shape=(None, 1024, n_dims, 1), name='X')
        self.y = tf.placeholder(tf.int32, shape=(None))


        with tf.name_scope('point_net'):
            # Implement T-net here


            self.net = tf.layers.conv2d(inputs=self.X, filters=64, kernel_size=(1,3), padding='valid',
                                        activation=tf.nn.relu, kernel_initializer=xavier_init)
            self.net = tf.layers.conv2d(inputs=self.net, filters=64, kernel_size=(1,1), padding='valid',
                                        activation=tf.nn.relu, kernel_initializer=xavier_init)

            # Implement second T-net here

            self.net = tf.layers.conv2d(inputs=self.net, filters=64, kernel_size=(1,1), padding='valid',
                                        activation=tf.nn.relu, kernel_initializer=xavier_init)
            self.net = tf.layers.conv2d(inputs=self.net, filters=128, kernel_size=(1, 1), padding='valid',
                                        activation=tf.nn.relu, kernel_initializer=xavier_init)
            self.net = tf.layers.conv2d(inputs=self.net, filters=1024, kernel_size=(1, 1), padding='valid',
                                        activation=tf.nn.relu, kernel_initializer=xavier_init)

            self.net = tf.layers.max_pooling2d(self.net, pool_size=[self.args.n_points, 1],
                                               strides=(2,2), padding='valid')

            self.net = tf.layers.dense(self.net, 512, activation=tf.nn.relu,
                                       kernel_initializer=xavier_init)
            self.net = tf.layers.dense(self.net, 256, activation=tf.nn.relu,
                                       kernel_initializer=xavier_init)
            self.logits = tf.layers.dense(self.net, 10, activation=None,
                                       kernel_initializer=xavier_init)

        with tf.name_scope('loss'):
            self.xentropy = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=self.y, logits=self.logits)
            self.loss = tf.reduce_mean(self.xentropy)

        with tf.name_scope('train'):
            self.optimizer = tf.train.AdamOptimizer(learning_rate=self.args.learning_rate)
            self.training_op = self.optimizer.minimize(self.loss)



    def train(self):
        self.sess = tf.Session()
        self.sess.run(tf.global_variables_initializer())
        if self.args.load_checkpoint is not None:
            self.load()

        print('[*] Initializing training.')

        n_epochs = self.args.n_epochs
        batch_size = self.args.batch_size
        best_loss = np.infty
        max_checks_without_progress = self.args.early_stopping_max_checks
        checks_without_progres = 0

        for epoch in range(n_epochs):
            shuffle(self.train_list)
            for iteration in range(len(self.train_list) // self.args.batch_size):
                average_loss = list()
                iter_indices_begin = iteration * self.args.batch_size
                iter_indices_end = (iteration + 1) * self.args.batch_size
                X_batch, y_batch = get_points_and_class(self.train_list[iter_indices_begin:iter_indices_end],
                                                        self.class_dict, self.args.n_points)
                self.sess.run(self.training_op, feed_dict={self.X: X_batch[:,:,:,np.newaxis],
                                                      self.y: y_batch})
                iter_loss = self.sess.run(self.loss, feed_dict={self.X: X_batch[:,:,:,np.newaxis],
                                                  self.y: y_batch})
                average_loss.append(iter_loss)
            average_loss = sum(average_loss) / len(average_loss)
            print('Epoch: ', epoch, 'Average loss: ', average_loss)
            if epoch % 50 == 0:
                self.save(epoch)

    def test(self):
        pass

    def save(self, epoch):
        print('[*] Saving checkpoint ....')
        model_name = 'model_{}_epoch_{}.ckpt'.format(datetime.now().strftime("%d:%H:%M:%S"), epoch)
        self.saver = tf.train.Saver()
        save_path = self.saver.save(self.sess, os.path.join(self.args.saved_model_directory, model_name))
        print('[*] Checkpoint saved in file {}'.format(save_path))

    def load(self):
        print(" [*] Loading checkpoint...")
        self.saver = tf.train.Saver()
        self.saver.restore(self.sess, os.path.join(self.args.saved_model_directory, self.args.model_name))