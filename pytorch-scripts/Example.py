#Demo for CS7-GV1

#general modules
from __future__ import print_function, division
import os
import argparse
import time
import copy

#pytorch modules
import torch
import torch.nn as nn
from torchvision import datasets
from torch.optim.lr_scheduler import ReduceLROnPlateau
import torch.optim as optim
from torch.autograd import Variable


#user defined modules
import Augmentation as ag
import Models

parser = argparse.ArgumentParser(description='CS7-GV1 Final Project');



parser.add_argument('--aug', type=str, default = 'SCALE_H_FLIP', help='data augmentation strategy')
parser.add_argument('--datapath', type=str, default='', 
               help='root folder for data.It contains two sub-directories train and val')
parser.add_argument('--cuda', action='store_true',
                    help='use CUDA')               
parser.add_argument('--pretrained', action='store_true',
                    help='use pretrained model')
parser.add_argument('--batch_size', type=int, default = 128,
                    help='batch size')
parser.add_argument('--model', type=str, default = None, help='Specify model to use for training.')
parser.add_argument('--lr', type=float, default=0.001,
                    help='initial learning rate')
parser.add_argument('--epochs', type=int, default=25,
                    help='upper epoch limit')
args = parser.parse_args();
print (args)

#Define augmentation strategy
augmentation_strategy = ag.Augmentation(args.aug);
data_transforms = augmentation_strategy.applyTransforms();
##

#Root directory
data_dir = args.datapath;
##

######### Data Loader ###########
dsets = {x: datasets.ImageFolder(os.path.join(data_dir, x), data_transforms[x])
             for x in ['train', 'val']}
dset_loaders = {x: torch.utils.data.DataLoader(dsets[x], batch_size=args.batch_size,
                                               shuffle=True, num_workers=8)
             for x in ['train', 'val']}
                 
dset_sizes = {x: len(dsets[x]) for x in ['train', 'val']}
dset_classes = dsets['train'].classes
#################################

#set GPU flag
use_gpu = args.cuda;
##

#Load model
if args.model == "ResNet18":
    current_model = Models.resnet18(args.pretrained)
    num_ftrs = current_model.fc.in_features
    current_model.fc = nn.Linear(num_ftrs, len(dset_classes));
    
elif args.model == 'Demo':
    current_model = Models.demo_model();
else :
    print ("Model %s not found"%(args.model))
    exit();    


if use_gpu:
    current_model = current_model.cuda();
    

criterion = nn.CrossEntropyLoss()
optimizer_ft = optim.SGD(current_model.parameters(), lr=args.lr, momentum=0.9)
scheduler_ft = ReduceLROnPlateau(optimizer_ft, 'min', factor = 0.5,patience = 3, verbose = True)



def train_model(model, criterion, optimizer, lr_scheduler, num_epochs=25):
    since = time.time()

    best_model = model
    best_acc = 0.0
    for epoch in range(num_epochs):

        # Each epoch has a training and validation phase
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train(True)  # Set model to training mode
            else:
                model.train(False)  # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0
            # Iterate over data.
            for count, data in enumerate(dset_loaders[phase]):
                # get the inputs
                inputs, labels = data

                # wrap them in Variable
                if use_gpu:
                    inputs, labels = Variable(inputs.cuda()), \
                        Variable(labels.cuda())
                else:
                    inputs, labels = Variable(inputs), Variable(labels)

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                outputs = model(inputs)
                _, preds = torch.max(outputs.data, 1)
                
                loss = criterion(outputs, labels)

                # backward + optimize only if in training phase
                if phase == 'train':
                    loss.backward()
                    optimizer.step()

                # statistics
                
                running_loss += loss.data[0]
                running_corrects += torch.sum(preds == labels.data)
                #if count%10 == 0:
                #    print('Batch %d || Running Loss = %0.6f || Running Accuracy = %0.6f'%(count+1,running_loss/(args.batch_size*(count+1)),running_corrects/(args.batch_size*(count+1))))
                #print('Running Loss = %0.6f'%(running_loss/(args.batch_size*(count+1))))

            epoch_loss = running_loss / dset_sizes[phase]
            epoch_acc = running_corrects / dset_sizes[phase]
            

            print('Epoch %d || %s Loss: %.4f || Acc: %.4f'%(epoch,
                phase, epoch_loss, epoch_acc),end = ' || ')
            #pdb.set_trace();
            if phase == 'val':
                print ('\n', end='');
                lr_scheduler.step(epoch_loss);
            
            # deep copy the model
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model = copy.deepcopy(model)

    time_elapsed = time.time() - since
    print('\nTraining complete in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))
    return best_model

trained_model = train_model(current_model, criterion, optimizer_ft, scheduler_ft,
                      num_epochs=args.epochs);