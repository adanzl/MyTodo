export const createTriggerController = () => {
  let destroyTriggerInteraction: (() => void) | undefined;

  /**
   * Removes the click listener from the trigger element.
   */
  const removeClickListener = (): void => {
    if (destroyTriggerInteraction) {
      destroyTriggerInteraction();
      destroyTriggerInteraction = undefined;
    }
  };

  /**
   * Adds a click listener to the trigger element.
   * Presents the overlay when the trigger is clicked.
   * @param el The overlay element.
   * @param trigger The ID of the element to add a click listener to.
   */
  const addClickListener = (el: HTMLElement, trigger: string): void => {
    removeClickListener();

    const triggerEl = trigger !== undefined ? document.getElementById(trigger) : null;
    if (!triggerEl) {
      console.warn(
        `A trigger element with the ID "${trigger}" was not found in the DOM. The trigger element must be in the DOM when the "trigger" property is set on an overlay component.`,
        el
      );
      return;
    }

    const configureTriggerInteraction = (targetEl: HTMLElement, overlayEl: any) => {
      const openOverlay = () => {
        overlayEl.present();
      };
      targetEl.addEventListener("click", openOverlay);

      return () => {
        targetEl.removeEventListener("click", openOverlay);
      };
    };

    destroyTriggerInteraction = configureTriggerInteraction(triggerEl, el);
  };

  return {
    addClickListener,
    removeClickListener,
  };
};

export default {
  createTriggerController,
};
