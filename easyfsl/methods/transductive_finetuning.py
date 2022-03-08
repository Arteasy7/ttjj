import torch
from torch import Tensor, nn


from easyfsl.methods import FewShotClassifier
from easyfsl.utils import entropy


class TransductiveFinetuning(FewShotClassifier):
    """
    Implementation of Transductive Finetuning (ICLR 2020) https://arxiv.org/abs/1909.02729
    This is a transductive method.
    """

    def __init__(
        self,
        fine_tuning_steps: int = 25,
        fine_tuning_lr: float = 5e-5,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.fine_tuning_steps = fine_tuning_steps
        self.fine_tuning_lr = fine_tuning_lr

        self.prototypes = None
        self.support_features = None
        self.support_labels = None

    def process_support_set(
        self,
        support_images: torch.Tensor,
        support_labels: torch.Tensor,
    ):
        """
        Overrides process_support_set of FewShotClassifier.
        Args:
            support_images: images of the support set
            support_labels: labels of support set images
        """
        self.store_features_labels_and_prototypes(support_images, support_labels)

    def forward(
        self,
        query_images: Tensor,
    ) -> Tensor:
        query_features = self.backbone.forward(query_images)
        # Run adaptation
        self.prototypes.requires_grad_()
        optimizer = torch.optim.Adam([self.prototypes], lr=self.fine_tuning_lr)
        for _ in range(self.fine_tuning_steps):

            support_cross_entropy = nn.functional.cross_entropy(
                self.get_logits_from_euclidean_distances_to_prototypes(
                    self.support_features
                ),
                self.support_labels,
            )
            query_conditional_entropy = entropy(
                self.get_logits_from_euclidean_distances_to_prototypes(query_features)
            )
            loss = support_cross_entropy + query_conditional_entropy
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        return self.softmax_if_specified(
            self.get_logits_from_euclidean_distances_to_prototypes(query_features)
        ).detach()

    @staticmethod
    def is_transductive():
        return True
