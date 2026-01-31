describe('Smoke', () => {
  it('访问根路径可打开应用', () => {
    cy.visit('/')
    cy.get('ion-page').should('be.visible')
  })
})
